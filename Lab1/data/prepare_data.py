#!/usr/bin/env python3
"""Sinh du lieu cho Lab01 - Linux, Git & du lieu van ban.

Chay mot lenh duy nhat:

    python3 prepare_data.py all

Se tao ra trong thu muc hien tai:
    messy.tsv       - file TSV nho co day du cac ca kho (tab / newline / dau nhay
                      kep ben trong gia tri, BOM, dong trong) de test parser.
    big_log.tsv     - ban log lon (~60 MB) sinh tu correct_log.tsv, seed co dinh,
                      BAO DAM khong co gia tri nao chua ky tu xuong dong.
    git-practice/   - (dat o thu muc dang lam viec) mot thung chua Git nho de thuc hanh branch / merge conflict
                      / .gitignore / git bisect. Noi dung va thoi diem commit deu
                      co dinh nen ma hash cua moi commit la nhu nhau tren moi may.

Moi thu deu tinh tu correct_log.tsv, khong tai gi tu Internet.
"""
import argparse
import datetime
import os
import subprocess
import sys
from zlib import adler32

HERE = os.path.dirname(os.path.abspath(__file__))
CORRECT_LOG = os.path.join(HERE, 'correct_log.tsv')

FIELDS = ['Id', 'ParentIds', 'AuthorName', 'AuthorEmail', 'AuthorDate',
          'Subject', 'ChangedFiles']

# So ban sao dung de sinh big_log.tsv (130 ban ~ 60 MB).
N_COPIES = 130

DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
RFC2822 = '%a, %d %b %Y %H:%M:%S %z'


# ----------------------------------------------------------------- tien ich
def quote(value):
    """Quote mot gia tri theo quy uoc cua bai: chi quote khi can."""
    if any(c in value for c in ('\t', '\n', '\r', '"')):
        return '"' + value.replace('"', '""') + '"'
    return value


def parse_rfc2822(text):
    return datetime.datetime.strptime(text, RFC2822)


def format_rfc2822(moment):
    """In ngay theo chuan RFC2822 dung kieu cua `git log --pretty=%aD`:
    ten thu / thang bang tieng Anh, ngay KHONG co so 0 dem truoc."""
    offset = moment.utcoffset() or datetime.timedelta(0)
    total = int(offset.total_seconds())
    sign = '+' if total >= 0 else '-'
    total = abs(total)
    return (f'{DAYS[moment.weekday()]}, {moment.day} '
            f'{MONTHS[moment.month - 1]} {moment.year} '
            f'{moment.hour:02d}:{moment.minute:02d}:{moment.second:02d} '
            f'{sign}{total // 3600:02d}{(total % 3600) // 60:02d}')


def read_correct_log():
    """Doc correct_log.tsv (co quoting) thanh list cac dict."""
    with open(CORRECT_LOG, 'r', encoding='utf-8-sig') as f:
        text = f.read()
    rows, row, field = [], [], []
    i, n, in_quote = 0, len(text), False
    while i < n:
        c = text[i]
        if in_quote:
            if c == '"':
                if i + 1 < n and text[i + 1] == '"':
                    field.append('"')
                    i += 2
                    continue
                in_quote = False
                i += 1
                continue
            field.append(c)
            i += 1
            continue
        if c == '"' and not field:
            in_quote = True
            i += 1
            continue
        if c == '\t':
            row.append(''.join(field))
            field = []
            i += 1
            continue
        if c == '\n':
            row.append(''.join(field))
            field = []
            rows.append(row)
            row = []
            i += 1
            continue
        if c == '\r':
            i += 1
            continue
        field.append(c)
        i += 1
    if field or row:
        row.append(''.join(field))
        rows.append(row)
    rows = [r for r in rows if r != ['']]
    header, data = rows[0], rows[1:]
    return [dict(zip(header, r)) for r in data]


# --------------------------------------------------------------- messy.tsv
MESSY_ROWS = [
    # (Id, Subject, ChangedFiles) - phan con lai dien tu dong
    ('aaa0001', 'Sua loi phan tich cu phap', 'a.py'),
    ('aaa0002', 'Them cot\tThoi luong vao bang', 'b.py,c.py'),
    ('aaa0003', 'Doi ten truong "id" thanh "commit_id"', 'd.py'),
    ('aaa0004', 'Viet lai mo ta:\nDong thu hai cua subject\nDong thu ba', 'e.py'),
    ('aaa0005', 'Ca kho nhat: co\ttab, co "nhay kep" va\nca xuong dong', 'f.py,g.py'),
]


def write_messy(out_dir):
    path = os.path.join(out_dir, 'messy.tsv')
    lines = ['\t'.join(FIELDS)]
    for idx, (cid, subject, files) in enumerate(MESSY_ROWS):
        row = [cid, 'bbb%04d' % idx, 'Nguyen Van A', 'a@example.com',
               format_rfc2822(datetime.datetime(
                   2024, 1, idx + 1, 10, 30, 0,
                   tzinfo=datetime.timezone(datetime.timedelta(hours=7)))),
               subject, files]
        lines.append('\t'.join(quote(v) for v in row))
    text = '\n'.join(lines) + '\n'
    # co y them BOM o dau file va mot dong trong o cuoi
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(text + '\n')
    return path


# ------------------------------------------------------------- big_log.tsv
def write_big_log(out_dir, n_copies=N_COPIES):
    records = read_correct_log()
    path = os.path.join(out_dir, 'big_log.tsv')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\t'.join(FIELDS) + '\n')
        for k in range(n_copies):
            for rec in records:
                new_id = '%07x' % (adler32(f'{k}:{rec["Id"]}'.encode())
                                   & 0xFFFFFFF)
                moment = parse_rfc2822(rec['AuthorDate'])
                moment += datetime.timedelta(days=k)
                name = rec['AuthorName']
                # cu 97 dong thi thay tac gia bang mot bot, cho du lieu do deu
                if (adler32(new_id.encode()) % 97) == 0:
                    name = 'bot-%d' % (k % 3)
                # big_log.tsv bao dam KHONG co gia tri nao chua xuong dong
                subject = rec['Subject'].replace('\n', ' ').replace('\r', ' ')
                row = [new_id, rec['ParentIds'], name, rec['AuthorEmail'],
                       format_rfc2822(moment), subject, rec['ChangedFiles']]
                f.write('\t'.join(quote(v) for v in row) + '\n')
    return path


# ------------------------------------------------------------ git-practice
COMMITS = [
    # (thong diep, noi dung moi cua stats.py)
    ('khoi tao du an', 'def tong(xs):\n    return sum(xs)\n'),
    ('them ham dem', 'def tong(xs):\n    return sum(xs)\n\n\ndef dem(xs):\n    return len(xs)\n'),
    ('them ham trung binh',
     'def tong(xs):\n    return sum(xs)\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / dem(xs)\n'),
    ('them ham lon nhat',
     'def tong(xs):\n    return sum(xs)\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / dem(xs)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'),
    ('them ham nho nhat',
     'def tong(xs):\n    return sum(xs)\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / dem(xs)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'
     '\n\ndef nho_nhat(xs):\n    return min(xs)\n'),
    ('them mo ta cho module',
     '"""Cac ham thong ke co ban."""\n\n\n'
     'def tong(xs):\n    return sum(xs)\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / dem(xs)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'
     '\n\ndef nho_nhat(xs):\n    return min(xs)\n'),
    ('them ham khoang',
     '"""Cac ham thong ke co ban."""\n\n\n'
     'def tong(xs):\n    return sum(xs)\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / dem(xs)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'
     '\n\ndef nho_nhat(xs):\n    return min(xs)\n'
     '\n\ndef khoang(xs):\n    return lon_nhat(xs) - nho_nhat(xs)\n'),
    ('toi uu ham tong',
     '"""Cac ham thong ke co ban."""\n\n\n'
     'def tong(xs):\n    ket_qua = 0\n    for x in xs:\n        ket_qua += x\n'
     '    return ket_qua\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / dem(xs)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'
     '\n\ndef nho_nhat(xs):\n    return min(xs)\n'
     '\n\ndef khoang(xs):\n    return lon_nhat(xs) - nho_nhat(xs)\n'),
    # >>> commit LAM HONG TEST: trung_binh chia cho dem(xs) - 1
    ('refactor ham trung binh',
     '"""Cac ham thong ke co ban."""\n\n\n'
     'def tong(xs):\n    ket_qua = 0\n    for x in xs:\n        ket_qua += x\n'
     '    return ket_qua\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / (dem(xs) - 1)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'
     '\n\ndef nho_nhat(xs):\n    return min(xs)\n'
     '\n\ndef khoang(xs):\n    return lon_nhat(xs) - nho_nhat(xs)\n'),
    ('them ham dem duy nhat',
     '"""Cac ham thong ke co ban."""\n\n\n'
     'def tong(xs):\n    ket_qua = 0\n    for x in xs:\n        ket_qua += x\n'
     '    return ket_qua\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / (dem(xs) - 1)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'
     '\n\ndef nho_nhat(xs):\n    return min(xs)\n'
     '\n\ndef khoang(xs):\n    return lon_nhat(xs) - nho_nhat(xs)\n'
     '\n\ndef dem_duy_nhat(xs):\n    return len(set(xs))\n'),
    ('them ham tich',
     '"""Cac ham thong ke co ban."""\n\n\n'
     'def tong(xs):\n    ket_qua = 0\n    for x in xs:\n        ket_qua += x\n'
     '    return ket_qua\n\n\ndef dem(xs):\n    return len(xs)\n'
     '\n\ndef trung_binh(xs):\n    return tong(xs) / (dem(xs) - 1)\n'
     '\n\ndef lon_nhat(xs):\n    return max(xs)\n'
     '\n\ndef nho_nhat(xs):\n    return min(xs)\n'
     '\n\ndef khoang(xs):\n    return lon_nhat(xs) - nho_nhat(xs)\n'
     '\n\ndef dem_duy_nhat(xs):\n    return len(set(xs))\n'
     '\n\ndef tich(xs):\n    ket_qua = 1\n    for x in xs:\n'
     '        ket_qua *= x\n    return ket_qua\n'),
    ('cap nhat README', None),
]

TEST_FILE = '''import stats

assert stats.tong([1, 2, 3, 4]) == 10
assert stats.dem([1, 2, 3, 4]) == 4
assert stats.trung_binh([1, 2, 3, 4]) == 2.5
print('OK')
'''

README_MAIN = ('# stats\n\nMot goi ham thong ke nho de thuc hanh Git.\n'
               '\n## Cach chay test\n\n    python3 test_stats.py\n')
README_FEATURE = ('# stats\n\nMot goi ham thong ke nho de thuc hanh Git.\n'
                  '\n## Huong dan cai dat\n\n    pip install -e .\n')
README_MAIN_EDIT = ('# stats\n\nMot goi ham thong ke nho de thuc hanh Git.\n'
                    '\n## Yeu cau\n\n    Python >= 3.10\n')

ENV = {
    'GIT_AUTHOR_NAME': 'Giang vien P4DS',
    'GIT_AUTHOR_EMAIL': 'p4ds@example.com',
    'GIT_COMMITTER_NAME': 'Giang vien P4DS',
    'GIT_COMMITTER_EMAIL': 'p4ds@example.com',
}


def git(repo, *args, check=True, env_extra=None):
    env = dict(os.environ)
    env.update(ENV)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(['git', '-C', repo, *args], check=check, env=env,
                          capture_output=True, text=True)


def write_practice_repo(out_dir):
    repo = os.path.join(out_dir, 'git-practice')
    if os.path.exists(repo):
        subprocess.run(['rm', '-rf', repo], check=True)
    os.makedirs(repo)
    git(repo, 'init', '--quiet', '--initial-branch=main')
    git(repo, 'config', 'commit.gpgsign', 'false')
    # dat san danh tinh de sinh vien commit duoc ma khong can cau hinh git toan cuc
    git(repo, 'config', 'user.name', 'Sinh vien P4DS')
    git(repo, 'config', 'user.email', 'sinhvien@example.com')

    base = datetime.datetime(2026, 1, 1, 9, 0, 0,
                             tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
    for i, (message, content) in enumerate(COMMITS):
        if content is not None:
            with open(os.path.join(repo, 'stats.py'), 'w') as f:
                f.write(content)
        else:
            with open(os.path.join(repo, 'README.md'), 'w') as f:
                f.write(README_MAIN)
        if i == 0:
            with open(os.path.join(repo, 'test_stats.py'), 'w') as f:
                f.write(TEST_FILE)
            with open(os.path.join(repo, 'README.md'), 'w') as f:
                f.write('# stats\n')
        when = (base + datetime.timedelta(days=i)).strftime('%Y-%m-%dT%H:%M:%S%z')
        git(repo, 'add', '-A')
        git(repo, 'commit', '--quiet', '-m', message,
            env_extra={'GIT_AUTHOR_DATE': when, 'GIT_COMMITTER_DATE': when})

    # nhanh feature/doc sua README theo mot huong khac -> merge se xung dot
    git(repo, 'checkout', '--quiet', '-b', 'feature/doc', 'HEAD~1')
    with open(os.path.join(repo, 'README.md'), 'w') as f:
        f.write(README_FEATURE)
    when = (base + datetime.timedelta(days=len(COMMITS))).strftime(
        '%Y-%m-%dT%H:%M:%S%z')
    git(repo, 'add', '-A')
    git(repo, 'commit', '--quiet', '-m', 'bo sung huong dan cai dat',
        env_extra={'GIT_AUTHOR_DATE': when, 'GIT_COMMITTER_DATE': when})

    # main sua tiep README o cung cho -> dam bao co xung dot that
    git(repo, 'checkout', '--quiet', 'main')
    with open(os.path.join(repo, 'README.md'), 'w') as f:
        f.write(README_MAIN_EDIT)
    when = (base + datetime.timedelta(days=len(COMMITS) + 1)).strftime(
        '%Y-%m-%dT%H:%M:%S%z')
    git(repo, 'add', '-A')
    git(repo, 'commit', '--quiet', '-m', 'ghi ro yeu cau phien ban Python',
        env_extra={'GIT_AUTHOR_DATE': when, 'GIT_COMMITTER_DATE': when})

    # de lai mot file rac de sinh vien viet .gitignore
    with open(os.path.join(repo, 'chay_thu.log'), 'w') as f:
        f.write('day la file log sinh ra khi chay thu, khong nen commit\n')
    return repo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('what', nargs='?', default='all',
                        choices=['all', 'messy', 'big', 'practice'])
    parser.add_argument('--copies', type=int, default=N_COPIES,
                        help='so ban sao khi sinh big_log.tsv (mac dinh %d)'
                             % N_COPIES)
    args = parser.parse_args()
    out_dir = HERE

    if args.what in ('all', 'messy'):
        path = write_messy(out_dir)
        print('da tao %s (%d byte)' % (path, os.path.getsize(path)))
    if args.what in ('all', 'big'):
        if not os.path.exists(CORRECT_LOG):
            sys.exit('khong tim thay correct_log.tsv canh script nay')
        path = write_big_log(out_dir, args.copies)
        print('da tao %s (%.1f MB)'
              % (path, os.path.getsize(path) / 1024 ** 2))
    if args.what in ('all', 'practice'):
        # thung chua thuc hanh dat canh notebook (thu muc dang lam viec),
        # khong dat trong data/
        repo = write_practice_repo(os.getcwd())
        head = git(repo, 'rev-parse', 'HEAD').stdout.strip()
        print('da tao %s (main o %s)' % (repo, head[:7]))


if __name__ == '__main__':
    main()
