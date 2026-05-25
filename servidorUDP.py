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
        print(f"[RDT 3.0] ACK {seq} perdido (simulado)")
        return

    ack = f"ACK:{seq}"

    sock.sendto(ack.encode(), client_addr)

    print(f"[RDT 3.0] ACK enviado -> {seq}")


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

        # Simulação de perda de pacote
        if simular_perda():
            print("[RDT 3.0] Pacote perdido (simulado)")
            continue

        try:
            # Separação do cabeçalho seq|dados
            cabecalho, dados = pacote.split(b'|', 1)

            seq = int(cabecalho.decode())

        except:
            print("[RDT 3.0] Pacote inválido")
            continue

        print(f"[RDT 3.0] Pacote recebido -> SEQ {seq}")

    

        if seq == esperado:

            # Primeiro pacote = nome do arquivo
            if arquivo is None:

                nome_arquivo = dados.decode('utf-8', errors='ignore').strip()

                nome_arquivo = os.path.basename(nome_arquivo)

                novo_nome = PREFIXO + nome_arquivo

                arquivo = open(novo_nome, "wb")

                print(f"Recebendo arquivo: {novo_nome}")

            # Fim do arquivo
            elif dados == b'FIM_ARQUIVO':

                print("[RDT 3.0] Fim do arquivo recebido")

                enviar_ack(sock, client_addr, seq)

                arquivo.close()

                return novo_nome, client_addr

            # Dados normais
            else:

                arquivo.write(dados)

                print(f"[RDT 3.0] {len(dados)} bytes gravados")

            # Envia ACK do pacote correto
            enviar_ack(sock, client_addr, seq)

            # Alterna sequência esperada
            esperado = 1 - esperado


        else:

            print(f"[RDT 3.0] Pacote duplicado -> {seq}")

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

    print("Arquivo devolvido ao cliente")


def main():

    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    servidor.bind((HOST, PORT))

    print(f"Servidor UDP RDT 3.0 escutando em {HOST}:{PORT}")

    while True:

        try:

            # Recebe arquivo utilizando RDT 3.0
            caminho_arquivo, client_addr = receber_arquivo(servidor)

            print(f"Arquivo salvo como: {caminho_arquivo}")

            # Devolve o arquivo ao cliente
            # (mantido simples para compatibilidade)
            enviar_arquivo(
                servidor,
                client_addr,
                caminho_arquivo
            )

            print(f"Arquivo devolvido ao cliente: {client_addr}")

        except Exception as erro:

            print(f"[ERRO] {erro}")


if __name__ == "__main__":
    main()
