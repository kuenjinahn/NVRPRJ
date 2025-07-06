# 파일 생성일 변경 도구

## 개요

`change_file_date.py`는 파일의 생성일을 지정된 날짜로 변경하는 Python 스크립트입니다.

## 기능

- **Windows**: 실제 파일 생성일 변경 (pywin32 모듈 필요)
- **Linux/Mac**: 파일 수정일 변경 (생성일 변경은 제한적)
- 다양한 날짜 형식 지원
- 대화형 모드 및 명령행 인자 지원
- 변경 전후 시간 확인

## 설치

### Windows에서 실제 생성일 변경을 위한 모듈 설치

```bash
# 자동 설치 스크립트 실행
python install_requirements.py

# 또는 수동 설치
pip install pywin32
```

## 사용법

### 1. 명령행 인자 사용

```bash
# 기본 사용법
python change_file_date.py 파일경로 날짜

# 예시
python change_file_date.py test.txt 2025-01-15
python change_file_date.py "test file.txt" "2025-01-15 14:30:45"
python change_file_date.py --file test.txt --date "2025-01-15 14:30"
```

### 2. 대화형 모드

```bash
python change_file_date.py
```

실행 후 프롬프트에서 파일 경로와 날짜를 입력합니다.

### 3. 도움말 보기

```bash
python change_file_date.py --help
```

## 지원되는 날짜 형식

- `YYYY-MM-DD` (예: 2025-01-15)
- `YYYY-MM-DD HH:MM` (예: 2025-01-15 14:30)
- `YYYY-MM-DD HH:MM:SS` (예: 2025-01-15 14:30:45)
- `YYYY/MM/DD` (예: 2025/01/15)
- `YYYY/MM/DD HH:MM` (예: 2025/01/15 14:30)
- `YYYY/MM/DD HH:MM:SS` (예: 2025/01/15 14:30:45)

## 운영체제별 동작

### Windows
- **pywin32 설치됨**: 실제 파일 생성일, 접근일, 수정일 모두 변경
- **pywin32 미설치**: 수정일만 변경 (생성일 변경 불가)

### Linux/macOS
- 파일 수정일만 변경
- 생성일 변경은 파일시스템에 따라 제한적

## 사용 예시

### 예시 1: 기본 사용
```bash
python change_file_date.py test.txt 2025-01-15
```

### 예시 2: 시간 포함
```bash
python change_file_date.py video.mp4 "2025-01-15 14:30:45"
```

### 예시 3: 공백이 포함된 파일명
```bash
python change_file_date.py "my file.txt" "2025-01-15 14:30"
```

### 예시 4: 대화형 모드
```bash
python change_file_date.py
# 파일 경로를 입력하세요: test.txt
# 목표 날짜를 입력하세요: 2025-01-15
# 계속하시겠습니까? (y/N): y
```

## 출력 예시

### Windows (pywin32 설치됨)
```
=== 파일 생성일 변경 도구 ===
파일 경로를 입력하세요: test.txt
목표 날짜를 입력하세요 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS): 2025-01-15

변경 정보:
파일: C:\D\project\nvr\src\nvr\src\test.txt
목표 날짜: 2025-01-15 00:00:00
운영체제: Windows
Windows 생성일 변경: ✅ 지원됨 (pywin32 설치됨)
--------------------------------------------------
계속하시겠습니까? (y/N): y
Windows: 파일 생성일이 2025-01-15 00:00:00로 변경되었습니다.
파일: C:\D\project\nvr\src\nvr\src\test.txt
변경 전 수정시간: 2025-01-01 12:00:00
변경 후 수정시간: 2025-01-15 00:00:00
변경 후 생성시간: 2025-01-15 00:00:00

✅ 파일 날짜 변경이 완료되었습니다!
```

### Windows (pywin32 미설치)
```
Windows 생성일 변경: ⚠️ 제한됨 (pywin32 미설치)
  실제 생성일 변경을 위해 'pip install pywin32' 실행 권장
Windows: 파일 수정일이 2025-01-15 00:00:00로 변경되었습니다.
참고: 실제 생성일 변경을 위해서는 'pip install pywin32'를 실행하세요.
```

## 주의사항

1. **Windows 생성일 변경**: pywin32 모듈이 필요합니다
2. **권한**: 파일을 수정할 권한이 있어야 합니다
3. **백업**: 중요한 파일의 경우 변경 전 백업을 권장합니다
4. **파일 시스템**: 일부 파일 시스템에서는 생성일 변경이 제한될 수 있습니다

## 기술적 세부사항

- **Windows (pywin32)**: `win32file.SetFileTime()` 함수를 사용하여 실제 생성일 변경
- **Windows (기본)**: `os.utime()` 함수를 사용하여 수정일만 변경
- **Linux/macOS**: `os.utime()` 함수를 사용하여 수정일만 변경
- **에러 처리**: 파일 존재 여부, 권한, 날짜 형식 등 검증

## 문제 해결

### pywin32 설치 오류
```bash
# 관리자 권한으로 실행
pip install pywin32

# 또는 자동 설치 스크립트 사용
python install_requirements.py
```

### 파일을 찾을 수 없습니다
- 파일 경로가 정확한지 확인
- 절대 경로 사용 권장

### 권한 오류
- 파일에 대한 쓰기 권한 확인
- 관리자 권한으로 실행 시도

### 날짜 형식 오류
- 지원되는 날짜 형식 확인
- 시간 정보 포함 여부 확인

## 라이선스

이 스크립트는 자유롭게 사용, 수정, 배포할 수 있습니다. 