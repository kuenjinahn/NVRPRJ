#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
필요한 모듈 설치 스크립트
Windows에서 파일 생성일 변경 기능을 위해 pywin32 모듈을 설치합니다.
"""

import subprocess
import sys
import platform

def install_pywin32():
    """pywin32 모듈 설치"""
    try:
        print("pywin32 모듈을 설치합니다...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "pywin32"], 
                              capture_output=True, text=True, check=True)
        print("✅ pywin32 설치 완료!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ pywin32 설치 실패!")
        print(f"오류: {e.stderr}")
        return False

def verify_installation():
    """설치 확인"""
    try:
        import win32file
        import win32con
        import pywintypes
        print("✅ pywin32 모듈이 정상적으로 설치되었습니다!")
        return True
    except ImportError as e:
        print(f"❌ pywin32 모듈 확인 실패: {e}")
        return False

def main():
    print("=== Windows 파일 생성일 변경 도구 - 모듈 설치 ===")
    
    # 운영체제 확인
    if platform.system() != "Windows":
        print("이 스크립트는 Windows에서만 필요합니다.")
        print(f"현재 운영체제: {platform.system()}")
        return
    
    print("Windows에서 파일 생성일을 변경하려면 pywin32 모듈이 필요합니다.")
    print()
    
    # 현재 설치 상태 확인
    print("현재 설치 상태 확인 중...")
    if verify_installation():
        print("pywin32가 이미 설치되어 있습니다.")
        return
    
    # 설치 진행
    print("pywin32가 설치되지 않았습니다.")
    confirm = input("설치를 진행하시겠습니까? (y/N): ").strip().lower()
    
    if confirm not in ['y', 'yes', '예']:
        print("설치가 취소되었습니다.")
        return
    
    # 설치 실행
    if install_pywin32():
        print("\n설치 후 확인 중...")
        if verify_installation():
            print("\n🎉 모든 설치가 완료되었습니다!")
            print("이제 change_file_date.py를 사용하여 파일 생성일을 변경할 수 있습니다.")
        else:
            print("\n⚠️ 설치가 완료되었지만 확인에 실패했습니다.")
            print("시스템을 재시작한 후 다시 시도해보세요.")
    else:
        print("\n설치에 실패했습니다.")
        print("관리자 권한으로 실행하거나 수동으로 설치해보세요:")
        print("pip install pywin32")

if __name__ == "__main__":
    main() 