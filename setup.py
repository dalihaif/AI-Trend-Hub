#!/usr/bin/env python3
"""
setup.py - AI趋势雷达 环境安装与启动脚本
由 start.bat 自动调用，处理: Python 检测、便携版下载、依赖安装、服务器启动
"""
import os
import sys
import urllib.request
import zipfile
import subprocess
import threading
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 5000
PYPORTABLE_DIR = os.path.join(PROJECT_DIR, ".pyportable")


def run_cmd(cmd, check=True):
    """运行命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        if result.stderr:
            print(f"    错误: {result.stderr[:300]}")
        sys.exit(1)
    return result.returncode


def find_python():
    """查找可用的 Python，返回路径或 None"""
    # 1. 便携版
    portable_exe = os.path.join(PYPORTABLE_DIR, "python.exe")
    if os.path.exists(portable_exe):
        print(f"[OK] 找到便携 Python")
        return portable_exe

    # 2. 系统 Python / py 启动器
    for cmd in ["python", "py -3", "python3"]:
        try:
            r = subprocess.run(
                f'{cmd} -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)"',
                shell=True, capture_output=True
            )
            if r.returncode == 0:
                # 获取版本号
                r2 = subprocess.run(
                    f'{cmd} -c "import sys; print(str(sys.version_info.major)+chr(46)+str(sys.version_info.minor))"',
                    shell=True, capture_output=True, text=True
                )
                ver = r2.stdout.strip() if r2.returncode == 0 else "3.x"
                print(f"[OK] 检测到系统 Python {ver}")
                return cmd
        except Exception:
            pass

    return None


def download_file(url, dest):
    """下载文件"""
    print(f"  正在下载: {url}")
    urllib.request.urlretrieve(url, dest)
    size_mb = os.path.getsize(dest) / 1024 / 1024
    print(f"  下载完成 ({size_mb:.1f} MB)")


def install_portable_python():
    """下载并安装便携 Python"""
    print()
    print("=" * 50)
    print("  未检测到 Python，正在自动安装...")
    print("=" * 50)

    ver = "3.12.10"
    zip_name = f"python-{ver}-embed-amd64.zip"
    zip_url = f"https://www.python.org/ftp/python/{ver}/{zip_name}"
    zip_path = os.path.join(PYPORTABLE_DIR, zip_name)

    os.makedirs(PYPORTABLE_DIR, exist_ok=True)

    # 下载
    print("\n[1/4] 下载 Python 便携版 (约 12MB)...")
    try:
        download_file(zip_url, zip_path)
    except Exception as e:
        print(f"\n[错误] 下载失败: {e}")
        print("  请检查网络连接后重试。")
        input("\n按回车键退出...")
        sys.exit(1)

    # 解压
    print("\n[2/4] 解压 Python...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(PYPORTABLE_DIR)
        os.remove(zip_path)
        print("  解压完成!")
    except Exception as e:
        print(f"\n[错误] 解压失败: {e}")
        input("\n按回车键退出...")
        sys.exit(1)

    # 启用 site-packages
    print("\n[3/4] 配置 Python 环境...")
    for f in os.listdir(PYPORTABLE_DIR):
        if f.endswith("._pth"):
            pth_path = os.path.join(PYPORTABLE_DIR, f)
            with open(pth_path, 'r') as pf:
                content = pf.read()
            content = content.replace("#import site", "import site")
            with open(pth_path, 'w') as pf:
                pf.write(content)
            print(f"  已启用 site-packages")
            break

    # 安装 pip
    print("\n[4/4] 安装 pip 包管理器...")
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = os.path.join(PYPORTABLE_DIR, "get-pip.py")
    try:
        download_file(get_pip_url, get_pip_path)
        python_exe = os.path.join(PYPORTABLE_DIR, "python.exe")
        subprocess.run(
            [python_exe, get_pip_path, "--no-warn-script-location"],
            check=True
        )
        os.remove(get_pip_path)
        print("  pip 安装完成!")
    except Exception as e:
        print(f"\n[错误] pip 安装失败: {e}")
        input("\n按回车键退出...")
        sys.exit(1)

    print("\n  Python 环境安装完成!\n")
    return os.path.join(PYPORTABLE_DIR, "python.exe")


def check_and_install_deps(python_exe):
    """检查并安装项目依赖"""
    print("正在检查项目依赖...")

    # 检查核心依赖
    import_map = {
        "flask": "flask",
        "flask-sqlalchemy": "flask_sqlalchemy",
        "beautifulsoup4": "bs4",
        "lxml": "lxml",
        "requests": "requests",
        "apscheduler": "apscheduler",
        "readability-lxml": "readability",
    }

    missing = []
    for pkg, module in import_map.items():
        r = subprocess.run(
            f'"{python_exe}" -c "import {module}"',
            shell=True, capture_output=True
        )
        if r.returncode != 0:
            missing.append(pkg)

    if missing:
        print(f"  需要安装: {', '.join(missing)}")
        print("  首次安装需要 2~5 分钟，请耐心等待...\n")
        req_file = os.path.join(PROJECT_DIR, "requirements.txt")
        if os.path.exists(req_file):
            run_cmd(f'"{python_exe}" -m pip install --quiet --no-warn-script-location -r "{req_file}"')
        else:
            pkgs = " ".join(missing)
            run_cmd(f'"{python_exe}" -m pip install --quiet --no-warn-script-location {pkgs}')
        print("  核心依赖安装完成!\n")
    else:
        print("  核心依赖已就绪。")

    # 可选依赖: scrapling
    r = subprocess.run(
        f'"{python_exe}" -c "import scrapling"',
        shell=True, capture_output=True
    )
    if r.returncode != 0:
        print("  正在安装 Scrapling (可选，跳过不影响使用)...")
        r2 = subprocess.run(
            f'"{python_exe}" -m pip install --quiet --no-warn-script-location scrapling',
            shell=True, capture_output=True
        )
        if r2.returncode == 0:
            print("  Scrapling 安装完成!")
        else:
            print("  Scrapling 已跳过，将使用备用抓取引擎。")
    else:
        print("  Scrapling 已安装。")


def open_browser_delayed():
    """3秒后自动打开浏览器"""
    time.sleep(3)
    import webbrowser
    webbrowser.open(f"http://127.0.0.1:{PORT}")


def main():
    print("=" * 50)
    print("  AI趋势雷达 - 环境检查与启动")
    print("=" * 50)
    print()

    # 检查项目文件
    if not os.path.exists(os.path.join(PROJECT_DIR, "app.py")):
        print("\n[错误] 未找到 app.py")
        print("  请确保 start.bat 位于 AI-Trend-Hub 项目目录下。")
        input("\n按回车键退出...")
        sys.exit(1)

    # 查找 Python
    python_exe = find_python()
    if python_exe is None:
        python_exe = install_portable_python()

    # 安装依赖
    print()
    check_and_install_deps(python_exe)

    # 启动服务器
    print()
    print("=" * 50)
    print("  AI趋势雷达 启动中...")
    print("=" * 50)
    print()
    print(f"  本地访问:  http://127.0.0.1:{PORT}")
    print(f"  管理后台:  http://127.0.0.1:{PORT}/admin")
    print(f"  管理账号:  admin / admin123")
    print()
    print(f"  关闭方式: 按 Ctrl+C 或直接关闭此窗口")
    print("=" * 50)
    print()

    # 自动打开浏览器
    threading.Thread(target=open_browser_delayed, daemon=True).start()

    # 启动 Flask
    os.chdir(PROJECT_DIR)
    os.environ["PYTHONIOENCODING"] = "utf-8"
    subprocess.run(f'"{python_exe}" app.py', shell=True)

    # Flask 退出后
    print("\n[提示] 服务器已停止。")
    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
