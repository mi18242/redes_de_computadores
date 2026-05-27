import socket
import os
import random

HOST = '0.0.0.0'     # Faz o servidor escutar em todas as interfaces de rede
PORT = 5000          # Porta onde o servidor ficará disponível
BUFFER_SIZE = 1024   # Tamanho máximo de cada pacote
PREFIXO = "leilao_"  # Prefixo que será adicionado ao nome do arquivo recebido

# Probabilidade de perda simulada
LOSS_PROBABILITY = 0.3


def simular_perda():
    """
    Simula perda aleatória de pacotes ou ACKs.
    """
    return random.random() < LOSS_PROBABILITY


def enviar_ack(sock, client_addr, seq):
    """
    Envia ACK para o cliente no formato ACK:<seq>.
    Também simula perda de ACK.
    """

    # Simulação de perda do ACK
    if simular_perda():
        print(f"[SERVIDOR] ACK {seq} perdido (simulado)")
        return

    ack = f"ACK:{seq}"

    sock.sendto(ack.encode('utf-8'), client_addr)

    print(f"[SERVIDOR] ACK enviado {seq}")


def receber_arquivo(sock):
    """
    Recebe os pacotes utilizando RDT 3.0.
    O cliente envia no formato:
    seq|dados
    """

    esperado = 0
    arquivo = None
    novo_nome = None

    while True:
        # Recebe pacote UDP
        pacote, client_addr = sock.recvfrom(BUFFER_SIZE)

        if pacote == b'PRONTO_RECEBER':
            return "PRONTO_RECEBER", client_addr

        # Simulação de perda de pacote
        if simular_perda():
            print("[SERVIDOR] Pacote perdido (simulado)")
            continue

        try:
            # Separação do cabeçalho seq|dados
            cabecalho, dados = pacote.split(b'|', 1)
            seq = int(cabecalho.decode())

        except:
            print("[SERVIDOR] Pacote inválido")
            continue

        print(f"[SERVIDOR] Pacote recebido {seq}")

    
        if seq == esperado:
            # Primeiro pacote = nome do arquivo
            if arquivo is None:
                nome_arquivo = dados.decode('utf-8', errors='ignore').strip()
                nome_arquivo = os.path.basename(nome_arquivo)
                novo_nome = PREFIXO + nome_arquivo
                arquivo = open(novo_nome, "wb")

                print(f"[SERVIDOR] Recebendo arquivo: {novo_nome}")

            # Fim do arquivo
            elif dados == b'FIM_ARQUIVO':
                print("[SERVIDOR] Fim do arquivo")

                # Lembra do ACK final
                ack = f"ACK:{seq}"
                sock.sendto(ack.encode('utf-8'), client_addr)
                print(f"[SERVIDOR] ACK final enviado {seq}")

                arquivo.close()

                return novo_nome, client_addr

            # Dados normais
            else:
                arquivo.write(dados)

                print(f"[SERVIDOR] {len(dados)} bytes gravados")

            # Envia ACK do pacote correto
            enviar_ack(sock, client_addr, seq)

            # Alterna sequência esperada
            esperado = 1 - esperado


        else:
            print(f"[SERVIDOR] Pacote duplicado {seq}")

            # Reenvia ACK do último pacote válido
            enviar_ack(sock, client_addr, 1 - esperado)


def enviar_arquivo(sock, client_addr, caminho_arquivo):
    """
    Reenvia o arquivo ao cliente.
    Mantido igual à primeira entrega.
    """

    sock.sendto(
        os.path.basename(caminho_arquivo).encode('utf-8'),
        client_addr
    )

    with open(caminho_arquivo, "rb") as f:
        while True:
            bloco = f.read(BUFFER_SIZE)

            if not bloco:
                break

            sock.sendto(bloco, client_addr)

    sock.sendto(b'FIM_ARQUIVO', client_addr)

    print("[SERVIDOR] Arquivo devolvido ao cliente")


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.bind((HOST, PORT))

    print(f"[SERVIDOR] escutando em {HOST}:{PORT}")

    while True:
        try:
            # Recebe arquivo utilizando RDT 3.0
            caminho_arquivo, client_addr = receber_arquivo(servidor)

            print(f"[SERVIDOR] Arquivo salvo como: {caminho_arquivo}")

            # Devolve o arquivo ao cliente
            # (mantido simples para compatibilidade)
            servidor.settimeout(10)
            mensagem, _ = servidor.recvfrom(BUFFER_SIZE)
            if mensagem == b'PRONTO_RECEBER':
                enviar_arquivo(servidor, client_addr, caminho_arquivo)
            servidor.settimeout(None)

            print(f"Arquivo devolvido ao cliente: {client_addr}")

        except Exception as erro:
            print(f"[ERRO] {erro}")


if __name__ == "__main__":
    main()
