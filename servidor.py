import socket
import os
import threading
import time
import random
from queue import Queue, Empty

HOST = '0.0.0.0'     # Faz o servidor escutar em todas as interfaces de rede
PORT = 5000          # Porta onde o servidor ficará disponível
BUFFER_SIZE = 1024   # Tamanho máximo de cada pacote 
PREFIXO = "leilao_"  # Prefixo que será adicionado ao nome do arquivo recebido

# Configurações da terceira entrega
TEMPO_LEILAO_PADRAO = 60
TAXA_PERDA_PACOTE = 0.20
TIMEOUT_RDT = 2

# Estruturas compartilhadas do servidor
clientes = {}
leiloes_ativos = {}


def receber_arquivo(sock, nome_arquivo):
    """
    Recebe os fragmentos do cliente e salva o arquivo já com o prefixo leilao_.
    """
    nome_arquivo = os.path.basename(nome_arquivo)
    novo_nome = PREFIXO + nome_arquivo

    # Abre o arquivo em modo escrita binária
    with open(novo_nome, "wb") as f:
        while True:
            # Recebe um pacote de dados do cliente
            dados, _ = sock.recvfrom(BUFFER_SIZE)

            # Se receber o marcador de fim, encerra o loop
            if dados == b'FIM_ARQUIVO':
                break

            # Escreve os dados recebidos no arquivo
            f.write(dados)

    # Retorna o nome do arquivo salvo
    return novo_nome


def enviar_arquivo(sock, client_addr, caminho_arquivo):
    """
    Reenvia ao cliente o arquivo já salvo no servidor.
    Primeiro envia o nome do arquivo e depois os bytes em blocos de até 1024.
    """
    sock.sendto(os.path.basename(caminho_arquivo).encode('utf-8'), client_addr)

    with open(caminho_arquivo, "rb") as f:
        while True:
            bloco = f.read(BUFFER_SIZE)
            if not bloco:
                break
            sock.sendto(bloco, client_addr)

    sock.sendto(b'FIM_ARQUIVO', client_addr)


def criar_sessao_cliente(sock, client_addr):
    """
    Cria a estrutura de atendimento de um cliente e inicia a thread dedicada.
    """
    if client_addr in clientes:
        return

    clientes[client_addr] = {
        "fila_comandos": Queue(),
        "fila_acks": Queue(),
        "seq_esperado": 0,
        "seq_envio": 0,
        "ativa": True,
    }

    thread_cliente = threading.Thread(
        target=processar_cliente,
        args=(sock, client_addr),
        daemon=True
    )
    thread_cliente.start()
    clientes[client_addr]["thread"] = thread_cliente

    print(f"Nova thread criada para o cliente {client_addr}")


def pacote_perdido():
    """
    Simula perda aleatória de pacote no servidor.
    """
    return random.random() < TAXA_PERDA_PACOTE


def desempacotar_pacote(pacote):
    """
    Espera o formato: seq|dados
    Retorna (seq, dados) ou (None, None) se o pacote estiver inválido.
    """
    if b'|' not in pacote:
        return None, None

    seq_bruta, dados = pacote.split(b'|', 1)

    try:
        seq = int(seq_bruta.decode('utf-8', errors='ignore'))
    except ValueError:
        return None, None

    return seq, dados


def enviar_ack(sock, client_addr, seq):
    """
    Envia ACK do pacote recebido.
    """
    ack = f"ACK:{seq}".encode('utf-8')
    sock.sendto(ack, client_addr)


def enviar_rdt(sock, client_addr, mensagem_bytes):
    """
    Envio confiável do lado do servidor usando stop-and-wait.
    O formato do pacote é: seq|dados
    """
    sessao = clientes.get(client_addr)
    if not sessao:
        return

    seq = sessao["seq_envio"]

    while True:
        pacote = f"{seq}|".encode('utf-8') + mensagem_bytes
        sock.sendto(pacote, client_addr)

        try:
            ack = sessao["fila_acks"].get(timeout=TIMEOUT_RDT)
        except Empty:
            print(f"Timeout ao enviar pacote para {client_addr}. Reenviando...")
            continue

        if ack == f"ACK:{seq}".encode('utf-8'):
            sessao["seq_envio"] = 1 - seq
            break


def tratar_mensagem_comando(texto, client_addr):
    """
    Ponto de entrada para o processamento dos comandos.
    Esta parte pertence à Pessoa 2, então aqui fica apenas o gancho.
    """
    print(f"[{client_addr}] Mensagem recebida: {texto}")
    return None


def processar_cliente(sock, client_addr):
    """
    Thread dedicada a um cliente.
    Recebe pacotes encaminhados pelo despachante principal e aplica RDT 3.0.
    """
    sessao = clientes[client_addr]

    while sessao["ativa"]:
        try:
            pacote = sessao["fila_comandos"].get(timeout=1)
        except Empty:
            continue

        seq, dados = desempacotar_pacote(pacote)
        if seq is None:
            continue

        # Pacote novo esperado
        if seq == sessao["seq_esperado"]:
            texto = dados.decode('utf-8', errors='ignore')
            resposta = tratar_mensagem_comando(texto, client_addr)

            enviar_ack(sock, client_addr, seq)
            sessao["seq_esperado"] = 1 - sessao["seq_esperado"]

            # Se no futuro houver resposta para enviar ao cliente, ela sai daqui
            if resposta is not None:
                if isinstance(resposta, str):
                    resposta = resposta.encode('utf-8')
                enviar_rdt(sock, client_addr, resposta)

        # Pacote duplicado ou fora de ordem
        else:
            enviar_ack(sock, client_addr, 1 - sessao["seq_esperado"])


def receber_pacotes(sock):
    """
    Loop principal do servidor: recebe pacotes de todos os clientes e os distribui.
    Aqui entra a simulação de perdas aleatórias.
    """
    while True:
        dados, client_addr = sock.recvfrom(BUFFER_SIZE)

        # Simulação de perda no servidor
        if pacote_perdido():
            print(f"Pacote perdido simulado de {client_addr}")
            continue

        if client_addr not in clientes:
            criar_sessao_cliente(sock, client_addr)

        sessao = clientes[client_addr]

        # ACKs vão para a fila de ACKs
        if dados.startswith(b'ACK:'):
            sessao["fila_acks"].put(dados)
        else:
            sessao["fila_comandos"].put(dados)


def cronometro_leiloes():
    """
    Thread em background que reduz o tempo dos leilões ativos.
    A estrutura do leilão será preenchida pela Pessoa 2.
    """
    while True:
        time.sleep(1)

        if not leiloes_ativos:
            continue

        for id_item, leilao in list(leiloes_ativos.items()):
            if not leilao.get("ativo", True):
                continue

            tempo_restante = leilao.get("tempo_restante")
            if tempo_restante is None:
                continue

            if tempo_restante > 0:
                leilao["tempo_restante"] = tempo_restante - 1

            if leilao["tempo_restante"] <= 0:
                leilao["ativo"] = False
                print(f"Leilão encerrado para o item {id_item}")


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.bind((HOST, PORT))

    print(f"Servidor UDP escutando em {HOST}:{PORT}")

    thread_recebimento = threading.Thread(
        target=receber_pacotes,
        args=(servidor,),
        daemon=True
    )
    thread_recebimento.start()

    thread_timer = threading.Thread(
        target=cronometro_leiloes,
        daemon=True
    )
    thread_timer.start()

    # Mantém o processo principal vivo
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
