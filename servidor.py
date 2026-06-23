import socket
import os
import random

HOST = '0.0.0.0'     # Escuta em todas as interfaces
PORT = 5000          # Porta do servidor
BUFFER_SIZE = 1024   # Tamanho máximo do pacote UDP
PREFIXO = "leilao_"  # Prefixo do projeto
LOSS_PROBABILITY = 0.3
TIMEOUT_VAL = 1.0    # Tempo de espera por um ACK (1 segundo)

def simular_perda():
    """Simula perda aleatória de pacotes ou ACKs."""
    return random.random() < LOSS_PROBABILITY

def enviar_ack(sock, client_addr, seq):
    """Envia ACK para o cliente e simula perda."""
    if simular_perda():
        print(f"[RDT 3.0] ACK {seq} perdido (simulado)")
        return
    ack = f"ACK:{seq}"
    sock.sendto(ack.encode(), client_addr)
    print(f"[RDT 3.0] ACK enviado -> {seq}")

def receber_arquivo_rdt(sock):
    """Recebe pacotes do cliente utilizando RDT 3.0."""
    esperado = 0
    arquivo = None
    novo_nome = None
    client_addr = None

    while True:
        try:
            pacote, addr = sock.recvfrom(BUFFER_SIZE)
            client_addr = addr

            if simular_perda():
                print("[RDT 3.0] Pacote recebido foi ignorado (Perda simulada)")
                continue

            cabecalho, dados = pacote.split(b'|', 1)
            seq = int(cabecalho.decode())
            print(f"[RDT 3.0] Pacote recebido -> SEQ {seq}")

            if seq == esperado:
                if arquivo is None:
                    # Primeiro pacote contém o nome do arquivo
                    nome_arquivo = dados.decode('utf-8', errors='ignore').strip()
                    novo_nome = PREFIXO + os.path.basename(nome_arquivo)
                    arquivo = open(novo_nome, "wb")
                    print(f"Criando arquivo: {novo_nome}")
                elif dados == b'FIM_ARQUIVO':
                    print("[RDT 3.0] Fim do arquivo recebido com sucesso")
                    enviar_ack(sock, client_addr, seq)
                    arquivo.close()
                    return novo_nome, client_addr
                else:
                    arquivo.write(dados)
                
                enviar_ack(sock, client_addr, seq)
                esperado = 1 - esperado
            else:
                print(f"[RDT 3.0] Pacote duplicado (esperado {esperado}, veio {seq}). Reenviando ACK.")
                enviar_ack(sock, client_addr, 1 - esperado)

        except Exception as e:
            print(f"[ERRO RECEBIMENTO] {e}")

def enviar_arquivo_rdt(sock, client_addr, caminho_arquivo):
    """Envia o arquivo de volta ao cliente utilizando RDT 3.0 completo."""
    sock.settimeout(TIMEOUT_VAL)
    seq_atual = 0

    # Lista de blocos a enviar: Primeiro o Nome do Arquivo, depois o Conteúdo, depois o FIM
    blocos = [os.path.basename(caminho_arquivo).encode('utf-8')]
    
    # BUFFER_SIZE - 3 garante espaço para o cabeçalho '0|' ou '1|'
    with open(caminho_arquivo, "rb") as f:
        while True:
            bloco = f.read(BUFFER_SIZE - 3)
            if not bloco:
                break
            blocos.append(bloco)
    blocos.append(b'FIM_ARQUIVO')

    for bloco in blocos:
        pacote = f"{seq_atual}|".encode() + bloco
        
        while True:
            try:
                if simular_perda():
                    print(f"[RDT 3.0] Envio do pacote SEQ {seq_atual} falhou (Perda simulada)")
                else:
                    sock.sendto(pacote, client_addr)
                    print(f"[RDT 3.0] Pacote enviado -> SEQ {seq_atual}")

                # Espera pelo ACK correspondente
                ack_dados, _ = sock.recvfrom(BUFFER_SIZE)
                ack_msg = ack_dados.decode().strip()

                if ack_msg == f"ACK:{seq_atual}":
                    print(f"[RDT 3.0] ACK recebido com sucesso -> {ack_msg}")
                    break
                else:
                    print(f"[RDT 3.0] ACK incorreto recebido ({ack_msg}). Reenviando...")
            except socket.timeout:
                print(f"[TIMEOUT] Sem resposta para o pacote SEQ {seq_atual}. Retransmitindo...")

        seq_atual = 1 - seq_atual

    # Remove o timeout do socket para voltar ao modo bloqueante normal do servidor
    sock.settimeout(None)

def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.bind((HOST, PORT))
    print(f"Servidor UDP RDT 3.0 operando em {HOST}:{PORT}")

    while True:
        try:
            caminho_arquivo, client_addr = receber_arquivo_rdt(servidor)
            print(f"Arquivo salvo localmente como: {caminho_arquivo}")
            
            print(f"Iniciando devolução confiável para {client_addr}...")
            enviar_arquivo_rdt(servidor, client_addr, caminho_arquivo)
            print("-" * 50)
        except Exception as erro:
            print(f"[ERRO MAIN] {erro}")

if __name__ == "__main__":
    main()