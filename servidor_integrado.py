import socket
import os
import threading
import time
import random
from queue import Queue, Empty

# ==========================
# CONSTANTES E GLOBAIS
# ==========================
HOST = '0.0.0.0'     
PORT = 5000          
BUFFER_SIZE = 1024   
PREFIXO = "leilao_"  

# Configurações de RDT atualizadas (servidorUDP.py)
LOSS_PROBABILITY = 0.3
TIMEOUT_VAL = 1.0

# Estruturas compartilhadas do servidor (Pessoa 1 + Pessoa 2)
clientes = {}
leiloes_ativos = {}
usuarios_online = {}
proximo_id = 1


# ==========================
# REGRAS DE NEGÓCIO E INTERPRETADOR (Pessoa 2)
# ==========================
def fazer_login(nome, endereco):
    if nome in usuarios_online:
        return "ERRO: usuário já conectado"
    usuarios_online[nome] = endereco
    return "Você está online"

def fazer_logout(nome):
    if nome not in usuarios_online:
        return "ERRO: usuário não está online"
    del usuarios_online[nome]
    return "Logout realizado"

def criar_leilao(produto, preco, tempo):
    global proximo_id
    try:
        preco = float(preco)
        tempo = int(tempo)
    except:
        return "ERRO: valor inválido"

    if preco <= 0:
        return "ERRO: preço deve ser maior que zero"
    if tempo <= 0:
        return "ERRO: tempo inválido"

    leiloes_ativos[proximo_id] = {
        "produto": produto,
        "preco": preco,
        "lance_atual": preco,
        "tempo_restante": tempo, # Ajustado de 'tempo' para 'tempo_restante' para compatibilidade com Pessoa 1
        "ativo": True,
        "lances": 0
    }

    resposta = (
        f"Leilão criado\n"
        f"ID: {proximo_id}\n"
        f"Produto: {produto}\n"
        f"Preço inicial: {preco}"
    )
    proximo_id += 1
    return resposta

def listar_leiloes():
    if not leiloes_ativos:
        return "Nenhum leilão ativo"
    
    resposta = ""
    for id, item in leiloes_ativos.items():
        if item["ativo"]:
            resposta += (
                f"\nID: {id}"
                f"\nProduto: {item['produto']}"
                f"\nPreço: R${item['preco']}"
                f"\nTempo: {item.get('tempo_restante', 0)}s"
                f"\n"
            )
    return resposta

def dar_lance(usuario, id_item, valor):
    try:
        id_item = int(id_item)
        valor = float(valor)
    except:
        return "ERRO: dados inválidos"

    if usuario not in usuarios_online:
        return "ERRO: faça login primeiro"
    if id_item not in leiloes_ativos:
        return "ERRO: item inexistente"

    item = leiloes_ativos[id_item]
    if item["ativo"] == False:
        return "ERRO: leilão encerrado"
    if valor <= item["preco"]:
        return "ERRO: lance precisa ser maior que o atual"

    item["preco"] = valor
    item["maior_lance"] = usuario
    item["lances"] += 1

    if item["lances"] >= 5:
        item["ativo"] = False

    return (
        f"Lance aceito\n"
        f"Produto: {item['produto']}\n"
        f"Valor: R${valor}\n"
        f"Usuário: {usuario}"
    )

def tratar_comando(mensagem, usuario):
    partes = mensagem.split()
    if len(partes) == 0:
        return "Comando vazio"

    comando = partes[0]

    if comando == "login":
        return fazer_login(partes[1], usuario) # Aqui 'usuario' contem o client_addr
    elif comando == "logout":
        return fazer_logout(usuario)
    elif comando == "create":
        return criar_leilao(partes[1], partes[2], partes[3])
    elif comando == "list":
        return listar_leiloes()
    elif comando == "bid":
        return dar_lance(usuario, partes[1], partes[2])
    else:
        return "Comando inválido"


# ==========================
# RDT 3.0 E REDE (servidorUDP.py + Pessoa 1)
# ==========================
def simular_perda():
    """Simula perda aleatória de pacotes ou ACKs (Atualizado do servidorUDP)."""
    return random.random() < LOSS_PROBABILITY

def enviar_ack(sock, client_addr, seq):
    """Envia ACK para o cliente e simula perda (Atualizado do servidorUDP)."""
    if simular_perda():
        print(f"[RDT 3.0] ACK {seq} perdido (simulado)")
        return
    ack = f"ACK:{seq}"
    sock.sendto(ack.encode('utf-8'), client_addr)
    print(f"[RDT 3.0] ACK enviado -> {seq}")

def criar_sessao_cliente(sock, client_addr):
    """Cria a estrutura de atendimento de um cliente e inicia a thread dedicada."""
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

def desempacotar_pacote(pacote):
    """Espera o formato: seq|dados"""
    if b'|' not in pacote:
        return None, None
    seq_bruta, dados = pacote.split(b'|', 1)
    try:
        seq = int(seq_bruta.decode('utf-8', errors='ignore'))
    except ValueError:
        return None, None
    return seq, dados

def enviar_rdt(sock, client_addr, mensagem_bytes):
    """Envio confiável do lado do servidor usando stop-and-wait por thread."""
    sessao = clientes.get(client_addr)
    if not sessao:
        return

    seq = sessao["seq_envio"]
    while True:
        pacote = f"{seq}|".encode('utf-8') + mensagem_bytes
        
        # Simula perda no envio do pacote também, mantendo consistência com RDT 3.0 atualizado
        if simular_perda():
            print(f"[RDT 3.0] Envio do pacote SEQ {seq} falhou (Perda simulada)")
        else:
            sock.sendto(pacote, client_addr)

        try:
            # Substituído TIMEOUT_RDT antigo pelo TIMEOUT_VAL atualizado
            ack_dados = sessao["fila_acks"].get(timeout=TIMEOUT_VAL)
            ack_msg = ack_dados.decode('utf-8', errors='ignore').strip()
            
            if ack_msg == f"ACK:{seq}":
                sessao["seq_envio"] = 1 - seq
                break
        except Empty:
            print(f"[TIMEOUT] Sem resposta para pacote SEQ {seq} de {client_addr}. Retransmitindo...")
            continue

def processar_cliente(sock, client_addr):
    """Thread dedicada a um cliente. Recebe comandos via fila e aplica RDT 3.0."""
    sessao = clientes[client_addr]

    while sessao["ativa"]:
        try:
            pacote = sessao["fila_comandos"].get(timeout=1)
        except Empty:
            continue

        seq, dados = desempacotar_pacote(pacote)
        if seq is None:
            continue

        if seq == sessao["seq_esperado"]:
            texto = dados.decode('utf-8', errors='ignore')
            
            # ADAPTAÇÃO NECESSÁRIA: Descobrir o nome do usuário a partir do endereço
            # para passar para o parser da Pessoa 2
            usuario_nome = client_addr
            for nome, addr in usuarios_online.items():
                if addr == client_addr:
                    usuario_nome = nome
                    break

            # Processa usando as regras de negócio da Pessoa 2
            resposta = tratar_comando(texto, usuario_nome)

            enviar_ack(sock, client_addr, seq)
            sessao["seq_esperado"] = 1 - sessao["seq_esperado"]

            if resposta is not None:
                if isinstance(resposta, str):
                    resposta = resposta.encode('utf-8')
                enviar_rdt(sock, client_addr, resposta)
        else:
            enviar_ack(sock, client_addr, 1 - sessao["seq_esperado"])

def receber_pacotes(sock):
    """Loop principal do servidor (Despachante)."""
    while True:
        dados, client_addr = sock.recvfrom(BUFFER_SIZE)

        # Atualizado para a função de perda probabilística da versão mais recente
        if simular_perda():
            print(f"[RDT 3.0] Pacote perdido simulado de {client_addr}")
            continue

        if client_addr not in clientes:
            criar_sessao_cliente(sock, client_addr)

        sessao = clientes[client_addr]

        if dados.startswith(b'ACK:'):
            sessao["fila_acks"].put(dados)
        else:
            sessao["fila_comandos"].put(dados)

def cronometro_leiloes():
    """Thread em background que reduz o tempo dos leilões ativos (Pessoa 1)."""
    while True:
        time.sleep(1)
        if not leiloes_ativos:
            continue

        # Convertido para list para evitar erros ao iterar um dicionário mutável
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
    print(f"Servidor UDP RDT 3.0 (Leilão Multiusuário) operando em {HOST}:{PORT}")

    thread_recebimento = threading.Thread(target=receber_pacotes, args=(servidor,), daemon=True)
    thread_recebimento.start()

    thread_timer = threading.Thread(target=cronometro_leiloes, daemon=True)
    thread_timer.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
