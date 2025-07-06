import socket
import time

# 카메라 IP 및 포트 설정
CAMERA_IP = '175.201.204.165'
CAMERA_PORT = 32000

# 패킷 생성 함수


def build_packet(cmd, data):
    print("[*] 패킷 구성 시작...")

    header = 0xFF
    address = 0x00
    cmd_h = (cmd >> 8) & 0xFF
    cmd_l = cmd & 0xFF
    data_h = (data >> 8) & 0xFF
    data_l = data & 0xFF

    print(f"    Header      : 0x{header:02X}")
    print(f"    Address     : 0x{address:02X}")
    print(f"    CMD_H       : 0x{cmd_h:02X}")
    print(f"    CMD_L       : 0x{cmd_l:02X}")
    print(f"    DATA_H
    # Checksum: Byte2~Byte6의 8bit 합
    payload = [address, cmd_h, cmd_l, data_h, data_l]
    checksum = sum(payload) & 0xFF
    print(f"    Checksum    : 0x{checksum:02X}")

    packet = bytes([header] + payload + [checksum])
    print(f"[*] 최종 패킷 (hex): {packet.hex()}")
    return packet

# 명령 전송 및 수신 함수


def send_command_and_receive(cmd, data):
    packet = build_packet(cmd, data)

    print(f"\n[*] 카메라에 연결 시도: {CAMERA_IP}:{CAMERA_PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(5)

        try:
            sock.connect((CAMERA_IP, CAMERA_PORT))
            print("[+] TCP 연결 성공")

            print("[*] 명령 전송 중...")
            sock.sendall(packet)
            print("[+] 명령 전송 완료")

            print("[*] 카메라 응답 대기 중...\n")
            while True:
                try:
                    data = sock.recv(1024)
                    if data:
                        print(f"[RECV {len(data)} bytes] {data.hex()}")
                    else:
                        print("[-] 수신 데이터 없음 (소켓은 열려 있음)")
                        break
                except socket.timeout:
                    print("[!] 수신 타임아웃 - 응답 없음")
                    break

        except Exception as e:
            print(f"[!] 오류 발생: {e}")
        finally:
            print("[*] 소켓 종료")


# 실행 부분
if __name__ == "__main__":
    try:
        cmd_input = input("CMD (16진수, 예: 2304): ").strip()
        data_input = input("DATA (16진수, 예: 0001): ").strip()

        cmd = int(cmd_input, 16)
        data = int(data_input, 16)

        send_command_and_receive(cmd, data)

    except ValueError:
        print("[!] 잘못된 입력입니다. 16진수 형식으로 입력하세요 (예: 2304, 0001)")
