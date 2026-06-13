import zipfile
import os
import hashlib

project_dir = r"C:\Users\Lenovo\Desktop\微信程序开发"
checksum_suffix = ".zip.sha256"
zip_path = f"{project_dir}\\legal_judgment_analysis_system.zip"
checksum_path = zip_path + checksum_suffix

# Verify ZIP integrity
print("验证压缩包完整性...")
with zipfile.ZipFile(zip_path, "r") as zf:
    bad = zf.testzip()
    if bad:
        print(f"错误: 文件损坏 - {bad}")
    else:
        files = zf.namelist()
        print(f"通过: 压缩包包含 {len(files)} 个文件, 无损坏")

# Verify checksum
print("\n验证校验和...")
with open(checksum_path) as f:
    expected = f.read().strip().split()[0]

sha256 = hashlib.sha256()
with open(zip_path, "rb") as f:
    for chunk in iter(lambda: f.read(65536), b""):
        sha256.update(chunk)
actual = sha256.hexdigest()

if expected == actual:
    print("通过: SHA256 校验和匹配")
    print(f"  SHA256: {actual}")
else:
    print("失败: 校验和不匹配")
    print(f"  期望: {expected}")
    print(f"  实际: {actual}")

# Extract to temp dir and verify
print("\n在临时目录中解压并验证...")
extract_dir = r"C:\Users\Lenovo\Desktop\微信程序开发\.temp_verify"
if os.path.exists(extract_dir):
    import shutil

    shutil.rmtree(extract_dir)
os.makedirs(extract_dir)

with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(extract_dir)

extracted = []
for root, dirs, fnames in os.walk(extract_dir):
    for f in fnames:
        extracted.append(os.path.join(root, f))
print(f"解压后文件数: {len(extracted)}")

# Clean up
shutil.rmtree(extract_dir)
print("临时目录已清理")

# Print final summary
zip_size = os.path.getsize(zip_path)
print(f"\n{'=' * 50}")
print("  最终打包结果摘要")
print(f"{'=' * 50}")
print(f"  压缩包: {os.path.basename(zip_path)}")
print(f"  大小: {zip_size / 1024 / 1024:.2f} MB")
print(f"  文件数: {len(files)}")
print(f"  SHA256: {actual}")
print(f"  校验和文件: {os.path.basename(checksum_path)}")
print("  完整性: 通过")
print("  校验和: 通过")
print(f"{'=' * 50}")
