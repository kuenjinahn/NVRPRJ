#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파일 생성일 변경 스크립트
파일명과 날짜를 입력하면 해당 파일의 생성일을 지정된 날짜로 변경합니다.
"""

import os
import sys
import argparse
from datetime import datetime
import platform

# Windows에서만 win32file 모듈 import
if platform.system() == "Windows":
    try:
        import win32file
        import win32con
        import pywintypes
        WINDOWS_AVAILABLE = True
    except ImportError:
        print("경고: win32file 모듈이 설치되지 않았습니다. Windows에서 생성일 변경이 제한됩니다.")
        print("설치 방법: pip install pywin32")
        WINDOWS_AVAILABLE = False
else:
    WINDOWS_AVAILABLE = False

def change_file_date(file_path, target_date):
    """
    파일의 생성일을 지정된 날짜로 변경
    
    Args:
        file_path (str): 변경할 파일 경로
        target_date (datetime): 목표 날짜
    
    Returns:
        bool: 성공 여부
    """
    try:
        if not os.path.exists(file_path):
            print(f"오류: 파일을 찾을 수 없습니다 - {file_path}")
            return False
        
        # 파일 정보 가져오기
        stat_info = os.stat(file_path)
        
        # 현재 시간 정보
        current_atime = stat_info.st_atime  # 접근 시간
        current_mtime = stat_info.st_mtime  # 수정 시간
        
        # 목표 날짜를 timestamp로 변환
        target_timestamp = target_date.timestamp()
        
        # 운영체제별 처리
        system = platform.system()
        
        if system == "Windows" and WINDOWS_AVAILABLE:
            # Windows에서 실제 생성일 변경
            try:
                # 파일 핸들 열기
                handle = win32file.CreateFile(
                    file_path,
                    win32con.GENERIC_WRITE,
                    0,  # 공유 모드
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_ATTRIBUTE_NORMAL,
                    None
                )
                
                # 파일 시간 구조체 생성
                filetime = pywintypes.Time(target_date)
                
                # 생성일, 접근일, 수정일 모두 변경
                win32file.SetFileTime(handle, filetime, filetime, filetime)
                
                # 파일 핸들 닫기
                handle.Close()
                
                print(f"Windows: 파일 생성일이 {target_date.strftime('%Y-%m-%d %H:%M:%S')}로 변경되었습니다.")
                
            except Exception as e:
                print(f"Windows 생성일 변경 실패: {str(e)}")
                print("수정일만 변경합니다...")
                # 실패 시 수정일만 변경
                os.utime(file_path, (target_timestamp, target_timestamp))
                print(f"Windows: 파일 수정일이 {target_date.strftime('%Y-%m-%d %H:%M:%S')}로 변경되었습니다.")
                
        elif system == "Windows" and not WINDOWS_AVAILABLE:
            # win32file이 없는 경우 수정일만 변경
            os.utime(file_path, (target_timestamp, target_timestamp))
            print(f"Windows: 파일 수정일이 {target_date.strftime('%Y-%m-%d %H:%M:%S')}로 변경되었습니다.")
            print("참고: 실제 생성일 변경을 위해서는 'pip install pywin32'를 실행하세요.")
            
        elif system == "Linux" or system == "Darwin":
            # Linux/Mac에서는 수정일만 변경 (생성일 변경은 파일시스템에 따라 제한적)
            os.utime(file_path, (target_timestamp, target_timestamp))
            print(f"Linux/Mac: 파일 수정일이 {target_date.strftime('%Y-%m-%d %H:%M:%S')}로 변경되었습니다.")
            print("참고: Linux/Mac에서는 생성일 변경이 제한적입니다.")
            
        else:
            print(f"지원하지 않는 운영체제: {system}")
            return False
        
        # 변경 확인
        new_stat_info = os.stat(file_path)
        print(f"파일: {file_path}")
        print(f"변경 전 수정시간: {datetime.fromtimestamp(current_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"변경 후 수정시간: {datetime.fromtimestamp(new_stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Windows에서 생성일 확인 (가능한 경우)
        if system == "Windows" and WINDOWS_AVAILABLE:
            try:
                handle = win32file.CreateFile(
                    file_path,
                    win32con.GENERIC_READ,
                    0,
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_ATTRIBUTE_NORMAL,
                    None
                )
                
                creation_time, access_time, write_time = win32file.GetFileTime(handle)
                handle.Close()
                
                creation_datetime = datetime.fromtimestamp(creation_time.timestamp())
                print(f"변경 후 생성시간: {creation_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                print(f"생성일 확인 실패: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return False

def parse_date(date_string):
    """
    날짜 문자열을 datetime 객체로 파싱
    
    Args:
        date_string (str): 날짜 문자열 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS)
    
    Returns:
        datetime: 파싱된 날짜
    """
    try:
        # 다양한 날짜 형식 시도
        date_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y/%m/%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"지원하지 않는 날짜 형식: {date_string}")
        
    except Exception as e:
        print(f"날짜 파싱 오류: {str(e)}")
        print("지원되는 형식:")
        print("  YYYY-MM-DD (예: 2025-01-15)")
        print("  YYYY-MM-DD HH:MM (예: 2025-01-15 14:30)")
        print("  YYYY-MM-DD HH:MM:SS (예: 2025-01-15 14:30:45)")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='파일의 생성일을 지정된 날짜로 변경합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python change_file_date.py test.txt 2025-01-15
  python change_file_date.py "test file.txt" "2025-01-15 14:30:45"
  python change_file_date.py --file test.txt --date "2025-01-15 14:30"

주의사항:
  - Windows: pywin32 모듈이 설치되어야 실제 생성일 변경이 가능합니다
  - Linux/Mac: 파일시스템에 따라 생성일 변경이 제한적일 수 있습니다
        """
    )
    
    parser.add_argument('file', nargs='?', help='변경할 파일 경로')
    parser.add_argument('date', nargs='?', help='목표 날짜 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--file', '-f', help='변경할 파일 경로')
    parser.add_argument('--date', '-d', help='목표 날짜')
    
    args = parser.parse_args()
    
    # 인자 처리
    file_path = args.file or args.file
    date_string = args.date or args.date
    
    # 대화형 모드
    if not file_path:
        print("=== 파일 생성일 변경 도구 ===")
        file_path = input("파일 경로를 입력하세요: ").strip()
    
    if not date_string:
        date_string = input("목표 날짜를 입력하세요 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS): ").strip()
    
    if not file_path or not date_string:
        print("파일 경로와 날짜를 모두 입력해주세요.")
        sys.exit(1)
    
    # 날짜 파싱
    target_date = parse_date(date_string)
    
    # 파일 경로 정규화
    file_path = os.path.abspath(file_path)
    
    print(f"\n변경 정보:")
    print(f"파일: {file_path}")
    print(f"목표 날짜: {target_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"운영체제: {platform.system()}")
    
    # Windows에서 win32file 상태 표시
    if platform.system() == "Windows":
        if WINDOWS_AVAILABLE:
            print("Windows 생성일 변경: ✅ 지원됨 (pywin32 설치됨)")
        else:
            print("Windows 생성일 변경: ⚠️ 제한됨 (pywin32 미설치)")
            print("  실제 생성일 변경을 위해 'pip install pywin32' 실행 권장")
    
    print("-" * 50)
    
    # 확인
    confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes', '예']:
        print("취소되었습니다.")
        sys.exit(0)
    
    # 파일 날짜 변경
    success = change_file_date(file_path, target_date)
    
    if success:
        print("\n✅ 파일 날짜 변경이 완료되었습니다!")
    else:
        print("\n❌ 파일 날짜 변경에 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main() 