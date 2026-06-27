import socket
import sys
import select

BUFFER_SIZE = 1024
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000
TIMEOUT = 2


def limpar_buffer(sock):
    """Limpa pacotes pendentes no socket."""
    while True:
        prontos, _, _ = select.select([sock], [], [], 0)
        if not prontos:
            break
        try:
            sock.recvfrom(BUFFER_SIZE)
        except OSError:
            break


def verificar_broadcasts(sock):
    """Verifica se há broadcasts pendentes e os exibe."""
    while True:
        prontos, _, _ = select.select([sock], [], [], 0)
        if not prontos:
            break
        try:
            pacote, _ = sock.recvfrom(BUFFER_SIZE)
            if pacote.startswith(b'BROADCAST|'):
                mensagem = pacote.split(b'|', 1)[1].decode('utf-8')
                print(f"\n{'='*50}")
                print(f"📢 BROADCAST: {mensagem}")
                print(f"{'='*50}")
        except:
            break


def enviar_e_receber_rdt(sock, dados, seq):
    cabecalho = f"{seq}|".encode('utf-8')
    pacote = cabecalho + dados

    tentativas = 0
    max_tentativas = 10

    while tentativas < max_tentativas:
        tentativas += 1
        print(f"[CLIENTE] Enviando pacote {seq} (tentativa {tentativas})")
        sock.sendto(pacote, (SERVER_HOST, SERVER_PORT))

        while True:
            try:
                resposta, addr = sock.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                print(f"[CLIENTE] Timeout, reenviando pacote {seq}...")
                break

            # Se for broadcast, mostra e continua esperando
            if resposta.startswith(b'BROADCAST|'):
                mensagem = resposta.split(b'|', 1)[1].decode('utf-8')
                print(f"\n{'='*50}")
                print(f"📢 BROADCAST: {mensagem}")
                print(f"{'='*50}")
                continue

            resposta_str = resposta.decode('utf-8', errors='ignore')

            if resposta_str == f"ACK:{seq}":
                print(f"[CLIENTE] ACK {seq} recebido")
                resposta_servidor = aguardar_resposta(sock, seq)
                return True, resposta_servidor

            if b'|' in resposta:
                try:
                    cabecalho_resp, dados_resp = resposta.split(b'|', 1)
                    seq_resp = int(cabecalho_resp.decode())
                except:
                    continue

                if seq_resp == seq:
                    print(f"[CLIENTE] Resposta recebida diretamente (ACK perdido, SEQ {seq})")
                    ack = f"ACK:{seq}"
                    sock.sendto(ack.encode('utf-8'), (SERVER_HOST, SERVER_PORT))
                    return True, dados_resp.decode('utf-8')
                elif seq_resp == 1 - seq:
                    print(f"[CLIENTE] Pacote duplicado anterior (SEQ {seq_resp}), enviando ACK")
                    ack = f"ACK:{seq_resp}"
                    sock.sendto(ack.encode('utf-8'), (SERVER_HOST, SERVER_PORT))
                    continue
                else:
                    print(f"[CLIENTE] SEQ inesperado: {seq_resp}, ignorando")
                    continue

            print(f"[CLIENTE] Resposta inesperada: {resposta_str[:50]}")

    return False, "[ERRO] Número máximo de tentativas excedido"


def aguardar_resposta(sock, seq_esperado):
    tentativas = 0
    while tentativas < 5:
        try:
            pacote, server_addr = sock.recvfrom(BUFFER_SIZE)

            # Se for broadcast, mostra e continua esperando
            if pacote.startswith(b'BROADCAST|'):
                mensagem = pacote.split(b'|', 1)[1].decode('utf-8')
                print(f"\n{'='*50}")
                print(f"BROADCAST: {mensagem}")
                print(f"{'='*50}")
                continue

            if b'|' not in pacote:
                continue

            cabecalho, dados = pacote.split(b'|', 1)
            seq = int(cabecalho.decode())

            if seq == seq_esperado:
                ack = f"ACK:{seq}"
                sock.sendto(ack.encode('utf-8'), server_addr)
                print(f"[CLIENTE] ACK enviado para resposta SEQ {seq}")
                return dados.decode('utf-8')
            else:
                ultimo_ack = 1 - seq_esperado
                print(f"[CLIENTE] Resposta duplicada/atrasada ({seq}), enviando ACK {ultimo_ack}")
                ack = f"ACK:{ultimo_ack}"
                sock.sendto(ack.encode('utf-8'), server_addr)

        except socket.timeout:
            tentativas += 1
            print(f"[CLIENTE] Timeout aguardando resposta (tentativa {tentativas})")
            continue
        except Exception as e:
            return f"[ERRO] {e}"

    return "[AVISO] Não foi possível receber resposta do servidor (timeout)"


def main():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cliente.settimeout(TIMEOUT)

    seq_atual = 0

    print("=" * 60)
    print("          BEM-VINDO AO AUCTIONCIN          ")
    print("=" * 60)
    print("Comandos disponíveis:")
    print("  -> login <seu_nome>")
    print("  -> logout")
    print("  -> create <produto> <preço> <tempo_segundos>")
    print("  -> list")
    print("  -> bid <id_leilao> <seu_lance>")
    print("  -> status")
    print("  -> sair")
    print("-" * 60)

    try:
        while True:
            # Verifica broadcasts pendentes ANTES de pedir comando
            verificar_broadcasts(cliente)
            
            comando = input("\nDigite o comando: ").strip()

            if not comando:
                continue

            if comando.lower() == 'sair':
                print("Encerrando aplicação cliente. Até logo!")
                break

            limpar_buffer(cliente)
            sucesso, resposta = enviar_e_receber_rdt(cliente, comando.encode('utf-8'), seq_atual)
            seq_atual = 1 - seq_atual

            print("\n[RESPOSTA DO SERVIDOR]:")
            print(resposta if resposta else "[Sem resposta]")
            print("-" * 50)

            # Verifica broadcasts que chegaram durante o processamento
            verificar_broadcasts(cliente)

    except KeyboardInterrupt:
        print("\nCliente finalizado via teclado.")
    finally:
        cliente.close()


if __name__ == "__main__":
    main()
