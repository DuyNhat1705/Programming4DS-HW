"""Lab02 — kiểm tra (và nếu thiếu thì tải) file data/u.data của MovieLens 100k.

Chạy từ thư mục của bài:   python3 data/prepare_data.py

- Nếu data/u.data đã có: kiểm tra md5, in OK hoặc báo lỗi.
- Nếu chưa có: tải ml-100k.zip từ GroupLens (bản chính thức, không đổi từ 1998),
  lấy riêng file ml-100k/u.data, rồi kiểm tra md5.
Chỉ dùng thư viện chuẩn của Python.
"""
import hashlib
import io
import os
import sys
import urllib.request
import zipfile

URL = os.environ.get(
    "ML100K_URL", "https://files.grouplens.org/datasets/movielens/ml-100k.zip")
MD5 = "6e47046882bad158b0efbb84cd5cb987"   # md5 của u.data
N_BYTES = 1_979_173
HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "u.data")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download():
    print(f"Đang tải {URL} ...")
    with urllib.request.urlopen(URL, timeout=120) as resp:
        blob = resp.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        data = zf.read("ml-100k/u.data")
    with open(TARGET, "wb") as f:
        f.write(data)
    print(f"Đã ghi {TARGET} ({len(data):,} byte)")


def main():
    if not os.path.exists(TARGET):
        download()
    size = os.path.getsize(TARGET)
    digest = md5_of(TARGET)
    if digest == MD5 and size == N_BYTES:
        print(f"OK  {TARGET}  {size:,} byte  md5 {digest}")
        return 0
    print(f"SAI {TARGET}: {size:,} byte, md5 {digest} "
          f"(cần {N_BYTES:,} byte, md5 {MD5}). Xoá file rồi chạy lại.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
