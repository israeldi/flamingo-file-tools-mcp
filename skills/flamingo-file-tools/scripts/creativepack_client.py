#!/usr/bin/env python3
# Generated.
import argparse
import base64
import hashlib
import http.client
import io
import json
import os
import queue
import re
import socket
import ssl
import stat
import struct
import sys
import tempfile
import threading
import unicodedata
import zipfile
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

def json_bytes(value):
  return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')

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

def zip_members(data, count, expanded, member_max):
  try:
    end = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    if end < 0 or end + 22 > len(data):
      raise ValueError()
    _, disk, start_disk, disk_count, total_count, size, offset, comment = struct.unpack_from('<4s4H2IH', data, end)
    if end + 22 + comment != len(data) or disk or start_disk:
      raise ValueError()
    boundary = end
    if 65535 in (disk_count, total_count) or 4294967295 in (size, offset):
      signature, disk, location, disks = struct.unpack_from('<4sIQI', data, end - 20)
      if signature != b'PK\x06\x07' or disk or disks != 1:
        raise ValueError()
      fields = struct.unpack_from('<4sQ2H2I4Q', data, location)
      if fields[0] != b'PK\x06\x06' or fields[1] != 44 or fields[4] or fields[5] or (location + 56 != end - 20):
        raise ValueError()
      disk_count, total_count, size, offset = fields[6:10]
      boundary = location
    if disk_count != total_count or not 1 <= total_count <= count or offset + size != boundary:
      raise ValueError()
    cursor, limit = (offset, offset + size)
    for _ in range(total_count):
      if cursor + 46 > limit or data[cursor:cursor + 4] != b'PK\x01\x02':
        raise ValueError()
      lengths = struct.unpack_from('<3H', data, cursor + 28)
      cursor += 46 + sum(lengths)
    if cursor != limit:
      raise ValueError()
    members, names, total = ([], set(), 0)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
      entries = archive.infolist()
      if not 1 <= len(entries) <= count:
        raise ValueError()
      for info in entries:
        name = info.orig_filename
        if name != info.filename or name in names or control(name) or name.startswith(('/', '\\')) or ('\\' in name) or re.match('^[A-Za-z]:', name) or ('..' in name.split('/')) or (info.flag_bits & 1) or (info.compress_type not in (0, 8)) or stat.S_ISLNK(info.external_attr >> 16) or (not 0 <= info.file_size <= member_max) or (total + info.file_size > expanded):
          raise ValueError()
        names.add(name)
        with archive.open(info) as stream:
          value = stream.read(min(member_max, expanded - total) + 1)
          if len(value) != info.file_size or len(value) > member_max or total + len(value) > expanded:
            raise ValueError()
          if stream.read(1):
            raise ValueError()
        total += len(value)
        members.append((name, value, name.endswith('/')))
    return members
  except (Exception,):
    invalid()

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
DESCRIPTION = 'Optimize supported HTML5 ZIP images through RapidAPI. Separate subscription required; over-budget is a valid result.'

def options(p):
  p.add_argument('--budget-bytes', type=int, required=True)
  p.add_argument('--mode', choices=('lossless', 'balanced'), default='lossless')

def validate(args):
  if not integer(args.budget_bytes, 1024, 8 * MIB):
    fail('invalid_arguments', 'Budget must be an integer from 1024 to 8388608 bytes. No request was made.')

def tool(args):
  return 'creativepack_optimize'

def descriptors(args):
  return ('creativepack.p.rapidapi.com', '/v1/optimize', 8 * MIB, 16 * MIB, 60)

def image(data):
  return data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')

def perform(args, source, descriptor, key):
  try:
    before = zip_members(source, 256, 32 * MIB, 8 * MIB)
  except ClientError:
    fail('file_invalid', 'The input ZIP failed container or expanded-size checks. No request was made.')
  payload = json.dumps({'archive_base64': base64.b64encode(source).decode(), 'budget_bytes': args.budget_bytes, 'mode': args.mode}).encode()
  raw, _ = request(descriptor, payload, 'application/json; charset=utf-8', 'application/json', key)
  value = parse_json(raw)
  if not isinstance(value, dict) or set(value) != {'archive_base64', 'report'} or contains_secret(value, key):
    invalid()
  encoded, report = (value['archive_base64'], value['report'])
  if not isinstance(encoded, str) or len(encoded) > 11184812 or (not isinstance(report, dict)):
    invalid()
  try:
    output = base64.b64decode(encoded, validate=True)
  except (ValueError, UnicodeError):
    invalid()
  if not output or len(output) > 8 * MIB or len(output) > len(source) or (base64.b64encode(output).decode() != encoded) or (key.encode() in output):
    invalid()
  expected = {'schema_version': '1.0', 'status': 'within_budget' if len(output) <= args.budget_bytes else 'over_budget', 'requested_mode': args.mode, 'budget_bytes': args.budget_bytes, 'input_bytes': len(source), 'output_bytes': len(output), 'saved_bytes': len(source) - len(output), 'input_sha256': digest(source), 'output_sha256': digest(output)}
  if any((not equal(report.get(k), v) for k, v in expected.items())):
    invalid()
  after = zip_members(output, 256, 32 * MIB, 8 * MIB)
  if len(before) != len(after) or not isinstance(report.get('files'), list) or len(report['files']) != len(after):
    invalid()
  for first, last, item in zip(before, after, report['files']):
    if not isinstance(item, dict) or first[0] != last[0] or key.encode() in last[1]:
      invalid()
    facts = {'path': first[0], 'input_bytes': len(first[1]), 'output_bytes': len(last[1]), 'saved_bytes': len(first[1]) - len(last[1]), 'input_sha256': digest(first[1]), 'output_sha256': digest(last[1])}
    if item.get('kind') not in ('image', 'non_image', 'directory') or any((not equal(item.get(k), v) for k, v in facts.items())):
      invalid()
    if (item['kind'] != 'image' or not image(first[1]) or first[2]) and first[1] != last[1]:
      invalid()
  invariants = report.get('invariants')
  if not isinstance(invariants, dict) or any((invariants.get(k) is not True for k in ('same_entry_paths', 'non_image_bytes_unchanged', 'image_dimensions_unchanged', 'archive_not_larger'))):
    invalid()
  return ({k: report[k] for k in ('status', 'input_bytes', 'output_bytes', 'saved_bytes')}, [('optimized.zip', output, 'application/zip'), ('report.json', json_bytes(report), 'application/json')])
if __name__ == '__main__':
  sys.exit(main())
