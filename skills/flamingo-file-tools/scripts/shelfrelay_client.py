#!/usr/bin/env python3
# Generated.
import argparse
import datetime
import hashlib
import http.client
import json
import os
import queue
import re
import socket
import ssl
import stat
import sys
import tempfile
import threading
import unicodedata
MIB = 1024 * 1024
MAX_SAFE = 9007199254740991

class ClientError(Exception):

  def __init__(self, code, message, status=None):
    super().__init__(message)
    self.code, self.message, self.status = (code, message, status)

def fail(code, message, status=None):
  raise ClientError(code, message, status)

def invalid():
  fail('response_invalid', 'Invalid response; no result files created.')

def integer(value, low=0, high=MAX_SAFE):
  return type(value) in (int, float) and low <= value <= high and (value == int(value))

def equal(left, right):
  return type(left) in (int, float) and left == right if type(right) in (int, float) else type(left) is type(right) and left == right

def control(value):
  return any((unicodedata.category(c).startswith('C') for c in value))

def digest(value):
  return hashlib.sha256(value).hexdigest()

def parse_json(data):

  def pairs(items):
    result = {}
    for key, value in items:
      if key in result:
        raise ValueError()
      result[key] = value
    return result
  try:
    value = json.loads(data.decode('utf-8', errors='strict'), object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    pending = [(value, 0)]
    while pending:
      item, depth = pending.pop()
      if depth > 64:
        raise ValueError()
      if isinstance(item, dict):
        pending.extend(((child, depth + 1) for child in item.values()))
      elif isinstance(item, list):
        pending.extend(((child, depth + 1) for child in item))
    return value
  except (ValueError, UnicodeError, RecursionError):
    invalid()

def contains_secret(value, key):
  if isinstance(value, str):
    return key in value
  if isinstance(value, list):
    return any((contains_secret(v, key) for v in value))
  if isinstance(value, dict):
    return any((key in k or contains_secret(v, key) for k, v in value.items()))
  return False

def _same(a, b):
  return a.st_dev == b.st_dev and a.st_ino == b.st_ino

def _within(root, path):
  try:
    return os.path.commonpath((root, path)) == root
  except ValueError:
    return False

def _trusted(info):
  return stat.S_ISDIR(info.st_mode) and (os.name == 'nt' or (info.st_uid == os.getuid() and (not info.st_mode & 18)))

def _root_check(root):
  current = os.lstat(root[1])
  if not _trusted(current) or not _same(current, root[2]) or os.path.realpath(root[1]) != root[1]:
    raise ValueError()

def workspace(directory):
  if not isinstance(directory, str) or not directory or control(directory):
    fail('workspace_missing', 'Select an existing private workspace.')
  try:
    configured = os.path.abspath(directory)
    root = os.path.realpath(configured)
    info = os.lstat(root)
    if not _trusted(info):
      raise ValueError()
    return (configured, root, info)
  except (OSError, ValueError):
    fail('workspace_invalid', 'Use an owned private workspace directory.')

def selected_file(root, selected, maximum):
  fd = None
  try:
    if not isinstance(selected, str) or not 1 <= len(selected.encode('utf-16-le')) // 2 <= 4096 or control(selected):
      raise ValueError()
    if '..' in re.split('[\\\\/]', selected):
      raise ValueError()
    path = os.path.abspath(os.path.join(root[1], selected))
    if os.path.isabs(selected) and _within(root[0], os.path.abspath(selected)):
      path = os.path.join(root[1], os.path.relpath(os.path.abspath(selected), root[0]))
    if not _within(root[1], path) or path == root[1]:
      raise ValueError()
    _root_check(root)
    cursor = root[1]
    for part in os.path.relpath(path, root[1]).split(os.sep):
      cursor = os.path.join(cursor, part)
      info = os.lstat(cursor)
      if stat.S_ISLNK(info.st_mode) or (cursor != path and (not _trusted(info))):
        raise ValueError()
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size < 1:
      raise ValueError()
    if before.st_size > maximum:
      fail('file_too_large', 'Input exceeds limit. No request was made.')
    if os.path.realpath(path) != path or not _same(before, os.lstat(path)):
      raise ValueError()
    chunks, remaining = ([], before.st_size + 1)
    while remaining:
      chunk = os.read(fd, min(remaining, 1024 * 1024))
      if not chunk:
        break
      chunks.append(chunk)
      remaining -= len(chunk)
    data = b''.join(chunks)
    after, named = (os.fstat(fd), os.lstat(path))
    if len(data) != before.st_size or after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns or (after.st_ctime_ns != before.st_ctime_ns) or (not _same(before, after)) or (not _same(before, named)) or stat.S_ISLNK(named.st_mode) or (os.path.realpath(path) != path):
      raise ValueError()
    _root_check(root)
    return data
  except ClientError:
    raise
  except (OSError, ValueError, UnicodeError):
    fail('file_invalid', 'Unsafe workspace file. No request was made.')
  finally:
    if fd is not None:
      os.close(fd)

def key_file(selected):
  """Read only the explicit private credential, with no path/secret logging."""
  fd = None
  try:
    if not isinstance(selected, str) or not os.path.isabs(selected) or control(selected) or (len(selected) > 4096) or ('..' in re.split('[\\\\/]', selected)):
      raise ValueError()
    path = os.path.normpath(selected)
    uid = os.geteuid()
    parents, cursor = ([], os.path.dirname(path))
    while True:
      info = os.lstat(cursor)
      sticky_system = info.st_uid == 0 and info.st_mode & stat.S_ISVTX
      if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, uid) or (info.st_mode & 18 and (not sticky_system)):
        raise ValueError()
      parents.append((cursor, info))
      if cursor == os.path.dirname(path) and (info.st_uid != uid or info.st_mode & 63):
        raise ValueError()
      parent = os.path.dirname(cursor)
      if parent == cursor:
        break
      cursor = parent
    named = os.lstat(path)
    if not stat.S_ISREG(named.st_mode) or named.st_uid != uid or stat.S_IMODE(named.st_mode) not in (256, 384) or (not 1 <= named.st_size <= 513):
      raise ValueError()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    before = os.fstat(fd)
    if not _same(named, before) or not stat.S_ISREG(before.st_mode) or before.st_uid != uid or (stat.S_IMODE(before.st_mode) not in (256, 384)) or (not 1 <= before.st_size <= 513):
      raise ValueError()
    data = b''
    while len(data) <= before.st_size:
      chunk = os.read(fd, before.st_size + 1 - len(data))
      if not chunk:
        break
      data += chunk
    after, named_after = (os.fstat(fd), os.lstat(path))
    if len(data) != before.st_size or after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns or (after.st_ctime_ns != before.st_ctime_ns) or (after.st_mode != before.st_mode) or (after.st_uid != uid) or (not _same(before, after)) or (not _same(after, named_after)) or (not stat.S_ISREG(named_after.st_mode)) or (named_after.st_mode != after.st_mode) or (named_after.st_uid != uid) or (os.path.realpath(path) != path):
      raise ValueError()
    for directory, original in parents:
      current = os.lstat(directory)
      if not _same(original, current) or original.st_mode != current.st_mode or original.st_uid != current.st_uid or (original.st_gid != current.st_gid):
        raise ValueError()
    key = (data[:-1] if data.endswith(b'\n') else data).decode('ascii')
    if not re.fullmatch('[\\x21-\\x7e]{16,512}', key):
      raise ValueError()
    return key
  except (OSError, ValueError, UnicodeError):
    fail('key_file_invalid', 'Use an owned private stable regular key file and private parent; one valid key only.')
  finally:
    if fd is not None:
      os.close(fd)

def _transport(host, route, headers, body, maximum, timeout):
  done, cancelled, active = (queue.Queue(), threading.Event(), [])

  def exchange():
    conn, response = (None, None)
    try:
      conn = http.client.HTTPSConnection(host, timeout=timeout, context=ssl.create_default_context())
      active.append(conn)
      conn.connect()
      conn.auto_open = 0
      if cancelled.is_set():
        return
      conn.request('POST', route, body=body, headers=headers)
      response = conn.getresponse()
      active.append(response)
      received = {}
      for name, value in response.getheaders():
        name = name.lower()
        if name in received:
          if name not in ('x-content-type-options', 'referrer-policy'):
            invalid()
          continue
        received[name] = value
      chunks, size = ([], 0)
      if response.status == 200:
        while not cancelled.is_set():
          chunk = response.read1(min(65536, maximum + 1 - size))
          if not chunk:
            break
          size += len(chunk)
          if size > maximum:
            fail('response_too_large', 'Response exceeds limit; no results created.')
          chunks.append(chunk)
      if not cancelled.is_set():
        done.put((True, (response.status, received, b''.join(chunks))))
    except BaseException as error:
      if not cancelled.is_set():
        done.put((False, error))
    finally:
      if response is not None:
        response.close()
      if conn is not None:
        conn.close()
  threading.Thread(target=exchange, daemon=True).start()
  try:
    success, value = done.get(timeout=timeout)
    if success:
      return value
    raise value
  except (queue.Empty, KeyboardInterrupt):
    cancelled.set()
    for item in active:
      sock = getattr(item, 'sock', None) or getattr(getattr(getattr(item, 'fp', None), 'raw', None), '_sock', None)
      if sock is not None:
        try:
          sock.shutdown(socket.SHUT_RDWR)
        except OSError:
          pass
    fail('transport_failed', 'Request timed out/cancelled; allowance may be consumed. No retry.')

def request(descriptor, body, content_type, accept, key, extra=None, query=''):
  host, route, _, maximum, timeout = descriptor
  headers = {'X-RapidAPI-Key': key, 'X-RapidAPI-Host': host, 'Content-Type': content_type, 'Accept': accept, 'Accept-Encoding': 'identity', 'Content-Length': str(len(body))}
  headers.update(extra or {})
  try:
    status, received, output = _transport(host, route + query, headers, body, maximum, timeout)
  except ClientError:
    raise
  except (Exception, KeyboardInterrupt):
    fail('transport_failed', 'Request incomplete; allowance may be consumed. No automatic retry.')
  if type(status) is not int or not 100 <= status <= 599:
    invalid()
  if 300 <= status < 400:
    fail('redirect_refused', 'Redirect refused; credentials not forwarded.', status)
  if status != 200:
    code, message = {401: ('authentication_failed', 'RapidAPI authentication failed.'), 403: ('subscription_required', 'Selected API subscription required.'), 429: ('quota_exceeded', 'Quota reached; review this API plan before retrying.')}.get(status, ('service_rejected', 'Input rejected; allowance may be consumed.') if 400 <= status < 500 else ('service_unavailable', 'Service unavailable or unexpected status.'))
    fail(code, message + ' No automatic retry.', status)
  if not isinstance(output, bytes) or not output:
    invalid()
  if len(output) > maximum:
    fail('response_too_large', 'Response exceeds limit; no results created.')
  length = received.get('content-length')
  if length is not None and (not isinstance(length, str) or not re.fullmatch('[0-9]{1,9}', length) or int(length) != len(output)):
    invalid()
  if received.get('content-encoding', 'identity').lower() != 'identity' or received.get('content-type', '').split(';')[0].strip().lower() != accept or key.encode() in output:
    invalid()
  return (output, received)

def write_artifacts(root, values):
  directory, info, created = (None, None, [])
  try:
    _root_check(root)
    directory = tempfile.mkdtemp(prefix='flamingo-results-', dir=root[1])
    os.chmod(directory, 448)
    info = os.lstat(directory)
    _root_check(root)
    if not _trusted(info) or os.path.realpath(directory) != directory:
      raise ValueError()
    result = []
    for name, data, media in values:
      if not _same(os.lstat(directory), info) or os.path.realpath(directory) != directory:
        raise ValueError()
      path = os.path.join(directory, name)
      fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 384)
      created.append((path, os.fstat(fd)))
      try:
        os.chmod(fd, 384)
        if not _same(os.lstat(directory), info) or os.path.realpath(directory) != directory:
          raise ValueError()
        with os.fdopen(fd, 'wb', closefd=False) as stream:
          stream.write(data)
          stream.flush()
          os.fsync(fd)
        after, named = (os.fstat(fd), os.lstat(path))
        if after.st_size != len(data) or stat.S_ISLNK(named.st_mode) or (not _same(after, named)):
          raise ValueError()
      finally:
        os.close(fd)
      result.append({'path': path, 'bytes': len(data), 'sha256': digest(data), 'media_type': media})
    _root_check(root)
    if not _same(os.lstat(directory), info):
      raise ValueError()
    return result
  except Exception:
    for path, original in created:
      try:
        current = os.lstat(path)
        if not stat.S_ISLNK(current.st_mode) and _same(current, original):
          os.unlink(path)
      except OSError:
        pass
    if directory and info:
      try:
        current = os.lstat(directory)
        if not stat.S_ISLNK(current.st_mode) and _same(current, info):
          os.rmdir(directory)
      except OSError:
        pass
    fail('artifact_write_failed', 'Cannot write private results; allowance may be consumed.')

class Parser(argparse.ArgumentParser):

  def error(self, message):
    fail('invalid_arguments', 'Invalid arguments; see --help.')

def parser():
  value = Parser(description=DESCRIPTION, allow_abbrev=False)
  value.add_argument('--workspace', required=True)
  value.add_argument('--file', required=True)
  value.add_argument('--key-file', help='Explicit private key file; overrides RAPIDAPI_KEY without fallback.')
  value.add_argument('--consent-upload', action='store_true', help='Authorize upload and allowance use.')
  options(value)
  return value

def run(argv=None):
  args = parser().parse_args(argv)
  if not args.consent_upload:
    fail('consent_required', 'Upload/allowance consent required.')
  if os.name != 'posix':
    fail('platform_unsupported', 'POSIX host required. No request was made.')
  key = key_file(args.key_file) if args.key_file is not None else os.environ.get('RAPIDAPI_KEY', '')
  if not re.fullmatch('[\\x21-\\x7e]{16,512}', key):
    fail('key_missing', 'Set RAPIDAPI_KEY privately, never in chat.')
  if key in args.file or key in args.workspace or key in (args.key_file or '') or (key in (getattr(args, 'text', None) or '')):
    fail('invalid_arguments', 'Credential in path/label. No request made.')
  validate(args)
  root = workspace(args.workspace)
  if key in root[1]:
    fail('workspace_invalid', 'Credential in workspace path.')
  descriptor = descriptors(args)
  source = selected_file(root, args.file, descriptor[2])
  if key.encode('ascii') in source:
    fail('credential_input_refused', 'Selected input contains the credential. No request was made.')
  summary, values = perform(args, source, descriptor, key)
  artifacts = write_artifacts(root, values)
  return {'ok': True, 'tool': tool(args), 'artifacts': artifacts, 'summary': summary, 'artifact_content_is_untrusted': True, 'note': 'Review artifacts; no retries.'}

def main():
  try:
    result = run()
  except ClientError as error:
    detail = {'code': error.code, 'message': error.message}
    if error.status is not None:
      detail['http_status'] = error.status
    print(json.dumps({'ok': False, 'error': detail}))
    return 1
  except (Exception, KeyboardInterrupt):
    print(json.dumps({'ok': False, 'error': {'code': 'operation_failed', 'message': 'Operation failed; no retry.'}}))
    return 1
  print(json.dumps(result, ensure_ascii=True))
  return 0
DESCRIPTION = 'Preview a prepared ShelfRelay ONIX records/policy JSON envelope through RapidAPI. Separate subscription; no store writes.'
MERCHANT_FIELDS = {'title', 'description', 'regular_price', 'stock_status', 'contributors', 'publisher', 'publication_date', 'languages', 'subjects', 'cover_url', 'product_form', 'availability_code', 'publishing_status', 'price_includes_tax'}

def options(p):
  pass

def validate(args):
  pass

def tool(args):
  return 'shelfrelay_preview'

def descriptors(args):
  return ('shelfrelay-onix.p.rapidapi.com', '/v1/normalize', 8 * MIB, 32 * MIB, 120)

def envelope(source):
  try:
    value = parse_json(source)
    if not isinstance(value, dict) or set(value) != {'records', 'policy'}:
      raise ValueError()
    records, policy = (value['records'], value['policy'])
    if not isinstance(records, list) or not 1 <= len(records) <= 100 or (not isinstance(policy, dict)):
      raise ValueError()
    required = {'market_country', 'currency', 'price_type'}
    if not required <= set(policy) or set(policy) - required - {'as_of', 'supplier_id', 'merchant_owned_fields'}:
      raise ValueError()
    if not isinstance(policy['market_country'], str) or not re.fullmatch('[A-Z]{2}', policy['market_country']) or (not isinstance(policy['currency'], str)) or (not re.fullmatch('[A-Z]{3}', policy['currency'])) or (policy['price_type'] not in ('01', '02')):
      raise ValueError()
    if 'as_of' in policy:
      date = policy['as_of']
      if not isinstance(date, str) or not re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', date) or datetime.date.fromisoformat(date).isoformat() != date:
        raise ValueError()
    if 'supplier_id' in policy:
      supplier = policy['supplier_id']
      if not isinstance(supplier, dict) or set(supplier) != {'type', 'value'} or (not isinstance(supplier['type'], str)) or (not re.fullmatch('[0-9]{2}', supplier['type'])) or (not isinstance(supplier['value'], str)) or (not supplier['value'].strip()) or (len(supplier['value']) > 200):
        raise ValueError()
    if 'merchant_owned_fields' in policy:
      fields = policy['merchant_owned_fields']
      if not isinstance(fields, list) or any((not isinstance(f, str) or f not in MERCHANT_FIELDS for f in fields)) or len(set(fields)) != len(fields):
        raise ValueError()
    total = 0
    for record in records:
      if not isinstance(record, dict) or 'xml' not in record or set(record) - {'xml', 'previous_xml'}:
        raise ValueError()
      for text in record.values():
        if not isinstance(text, str):
          raise ValueError()
        size = len(text.encode('utf-8'))
        if size > 256 * 1024:
          fail('file_too_large', 'Each ShelfRelay XML record/state is limited to 256 KiB. No request was made.')
        total += size
    if total > 8 * MIB:
      fail('file_too_large', 'Combined ShelfRelay XML exceeds 8 MiB. No request was made.')
    return value
  except ClientError as error:
    if error.code == 'file_too_large':
      raise
  except (ValueError, TypeError, UnicodeError):
    pass
  fail('invalid_arguments', 'The selected file must contain an unambiguous UTF-8 ShelfRelay records/policy envelope. No request was made.')

def perform(args, source, descriptor, key):
  selected = envelope(source)
  output, _ = request(descriptor, source, 'application/json; charset=utf-8', 'application/json', key)
  value = parse_json(output)
  if not isinstance(value, dict) or contains_secret(value, key) or value.get('ok') is not True or (not isinstance(value.get('results'), list)) or (len(value['results']) != len(selected['records'])) or (not isinstance(value.get('summary'), dict)):
    invalid()
  ok, rejected = (0, 0)
  for index, result in enumerate(value['results']):
    if not isinstance(result, dict) or not equal(result.get('index'), index) or result.get('status') not in ('ok', 'rejected'):
      invalid()
    if result['status'] == 'ok':
      ok += 1
    else:
      rejected += 1
  summary = {'total': len(value['results']), 'ok': ok, 'rejected': rejected}
  if any((not equal(value['summary'].get(k), v) for k, v in summary.items())):
    invalid()
  return (summary, [('preview.json', output, 'application/json')])
if __name__ == '__main__':
  sys.exit(main())
