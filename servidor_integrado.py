import socket
import threading
import time
import random
from queue import Queue, Empty

HOST = '0.0.0.0'
PORT = 5000
BUFFER_SIZE = 1024
LOSS_PROBABILITY = 0.3
TIMEOUT_VAL = 2.0

# ==========================
# ESTADOS GLOBAIS
# ==========================
clientes = {}
leiloes_ativos = {}
usuarios_online = {}
proximo_id = 1

# ==========================
# LOCKS DE SEGURANÇA
# ==========================
lock_usuarios = threading.Lock()
lock_leiloes = threading.Lock()


# ==========================
# REGRAS DE NEGÓCIO
# ==========================
def fazer_login(nome, endereco):
    with lock_usuarios:
        if nome in usuarios_online:
            return "ERRO: usuário já conectado"
        usuarios_online[nome] = endereco
    print(f"[LOGIN] {nome} conectado de {endereco}")
    return "Você está online"

def fazer_logout(nome):
    with lock_usuarios:
        if nome not in usuarios_online:
            return "ERRO: usuário não está online"
        del usuarios_online[nome]
    print(f"[LOGOUT] {nome} desconectado")
    return "Logout realizado"

def criar_leilao(produto, preco, tempo, criador):
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

    with lock_usuarios:
        if criador not in usuarios_online:
            return "ERRO: faça login primeiro para criar leilões"

    with lock_leiloes:
        leiloes_ativos[proximo_id] = {
            "produto": produto,
            "preco": preco,
            "lance_atual": preco,
            "tempo_restante": tempo,
            "ativo": True,
            "lances": 0,
            "maior_lance": None,
            "criador": criador
        }
        id_leilao = proximo_id
        proximo_id += 1

    return (
        f"Leilão criado\n"
        f"ID: {id_leilao}\n"
        f"Produto: {produto}\n"
        f"Preço inicial: {preco}\n"
        f"Tempo: {tempo}s"
    )

def listar_leiloes():
    with lock_leiloes:
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

    with lock_usuarios:
        if usuario not in usuarios_online:
            return "ERRO: faça login primeiro"

    with lock_leiloes:
        if id_item not in leiloes_ativos:
            return "ERRO: item inexistente"

        item = leiloes_ativos[id_item]
        if not item["ativo"]:
            return "ERRO: leilão encerrado"
        if valor <= item["preco"]:
            return "ERRO: lance precisa ser maior que o atual"

        item["preco"] = valor
        item["maior_lance"] = usuario
        item["lances"] += 1

        produto = item["produto"]
        lances_atual = item["lances"]
        encerrou = False

        if item["lances"] >= 5:
            item["ativo"] = False
            encerrou = True

    msg_broadcast = f"{usuario} deu lance de R${valor} em {produto}! (Lance {lances_atual}/5)"
    broadcast(msg_broadcast)

    if encerrou:
        msg_encerramento = f"LEILÃO ENCERRADO! {produto} vendido para {usuario} por R${valor}!"
        broadcast(msg_encerramento)

    return (
        f"Lance aceito\n"
        f"Produto: {item['produto']}\n"
        f"Valor: R${valor}\n"
        f"Usuário: {usuario}"
    )

def status_leiloes():
    with lock_leiloes:
        if not leiloes_ativos:
            return "Nenhum leilão ativo"

        resposta = "=== STATUS ===\n"
        for id, item in leiloes_ativos.items():
            maior = item.get("maior_lance", "Ninguém")
            status = "ATIVO" if item["ativo"] else "ENCERRADO"
            resposta += (
                f"\nID {id}: {item['produto']}"
                f"\n  Status: {status}"
                f"\n  Vencedor: {maior}"
                f"\n  Preço: R${item['preco']}"
                f"\n"
            )
    return resposta

def tratar_comando(mensagem, usuario, endereco_real=None):
    """
    Processa comando. 
    'usuario' é o nome logado ou None.
    'endereco_real' é a tupla (ip, porta) do cliente, usada para login.
    """
    partes = mensagem.split()
    if len(partes) == 0:
        return "Comando vazio"

    comando = partes[0].lower()

    if comando == "login":
        if len(partes) < 2:
            return "ERRO: informe o nome do usuário"
        # Para login, usa o endereço REAL (tupla) para registrar
        addr = endereco_real if endereco_real else usuario
        return fazer_login(partes[1], addr)
    elif comando == "logout":
        return fazer_logout(usuario)
    elif comando == "create":
        if len(partes) < 4:
            return "ERRO: uso correto: create <produto> <preço> <tempo_segundos>"
        return criar_leilao(partes[1], partes[2], partes[3], usuario)
    elif comando == "list":
        return listar_leiloes()
    elif comando == "bid":
        if len(partes) < 3:
            return "ERRO: uso correto: bid <id_leilao> <valor>"
        return dar_lance(usuario, partes[1], partes[2])
    elif comando == "status":
        return status_leiloes()
    else:
        return "Comando inválido"


# ==========================
# BROADCAST - FIRE AND FORGET
# ==========================
def broadcast(mensagem):
    """Envia mensagem para todos os usuários online — SEM RDT/ACK."""
    with lock_usuarios:
        destinatarios = list(usuarios_online.items())
        print(f"[BROADCAST] Enviando para {len(destinatarios)} usuários: {mensagem[:60]}...")

    for nome, addr in destinatarios:
        print(f"[BROADCAST] Tentando enviar para {nome} em {addr} (tipo: {type(addr)})")
        sessao = clientes.get(addr)
        if sessao and sessao.get("ativa"):
            try:
                pacote = f"BROADCAST|{mensagem}".encode('utf-8')
                sock = sessao["sock"]
                
                # Enviar o Broadcast
                sock.sendto(pacote, addr)
                print(f"[BROADCAST] ✓ Enviado para {nome} em {addr}")
                
            except Exception as e:
                print(f"[BROADCAST ERRO] Falha ao enviar para {nome}: {e}")
        else:
            print(f"[BROADCAST] ✗ Cliente {nome} ({addr}) não encontrado ou inativo")
            # Limpa usuário "zumbi"
            with lock_usuarios:
                if nome in usuarios_online and usuarios_online.get(nome) == addr:
                    del usuarios_online[nome]
                    print(f"[BROADCAST] Limpado usuário zumbi: {nome}")


# ==========================
# RDT 3.0 - REDE
# ==========================
def simular_perda():
    return random.random() < LOSS_PROBABILITY

def enviar_ack(sock, client_addr, seq):
    if simular_perda():
        print(f"[SERVIDOR] ACK {seq} perdido (simulado)")
        return
    ack = f"ACK:{seq}"
    try:
        sock.sendto(ack.encode('utf-8'), client_addr)
        print(f"[SERVIDOR] ACK enviado {seq} para {client_addr}")
    except OSError:
        print(f"[SERVIDOR] Falha ao enviar ACK para {client_addr}")

def enviar_pacote_rdt(client_addr, mensagem_str):
    """Envio confiável para um cliente específico (respostas normais)."""
    mensagem_bytes = mensagem_str.encode('utf-8') if isinstance(mensagem_str, str) else mensagem_str

    sessao = clientes.get(client_addr)
    if not sessao:
        print(f"[ENVIO ERRO] Sessão não encontrada para {client_addr}")
        return

    seq = sessao["seq_envio"]
    pacote = f"{seq}|".encode('utf-8') + mensagem_bytes
    sock = sessao["sock"]

    while True:
        if simular_perda():
            print(f"[ENVIO] Pacote SEQ {seq} perdido (simulado) para {client_addr}")
        else:
            try:
                sock.sendto(pacote, client_addr)
                print(f"[ENVIO] Pacote enviado -> SEQ {seq} para {client_addr}")
            except OSError:
                print(f"[ENVIO] Cliente {client_addr} desconectado")
                return

        try:
            ack_dados = sessao["fila_acks"].get(timeout=TIMEOUT_VAL)
            ack_msg = ack_dados.decode('utf-8', errors='ignore').strip()
            if ack_msg == f"ACK:{seq}":
                sessao["seq_envio"] = 1 - seq
                print(f"[ENVIO] ACK {seq} confirmado, próximo seq = {sessao['seq_envio']}")
                break
        except Empty:
            print(f"[TIMEOUT] Sem ACK de {client_addr}, retransmitindo...")
            continue

def criar_sessao_cliente(sock, client_addr):
    if client_addr in clientes:
        print(f"[SESSAO] Cliente {client_addr} já existe")
        return

    clientes[client_addr] = {
        "fila_comandos": Queue(),
        "fila_acks": Queue(),
        "seq_esperado": 0,
        "seq_envio": 0,
        "ativa": True,
        "sock": sock,
    }

    thread_cliente = threading.Thread(
        target=processar_cliente,
        args=(sock, client_addr),
        daemon=True
    )
    thread_cliente.start()
    clientes[client_addr]["thread"] = thread_cliente
    print(f"[SESSAO] Nova thread criada para {client_addr}")

def processar_cliente(sock, client_addr):
    """Thread dedicada a um cliente."""
    sessao = clientes[client_addr]
    usuario_atual = None

    while sessao["ativa"]:
        try:
            pacote = sessao["fila_comandos"].get(timeout=1)
        except Empty:
            continue

        if b'|' not in pacote:
            continue

        try:
            cabecalho, dados = pacote.split(b'|', 1)
            seq = int(cabecalho.decode())
        except:
            continue

        if seq == sessao["seq_esperado"]:
            texto = dados.decode('utf-8', errors='ignore')
            print(f"[PROCESSAR] Comando de {client_addr}: {texto[:40]}")

            # Atualiza usuario_atual se for login
            if texto.lower().startswith("login "):
                partes = texto.split()
                if len(partes) >= 2:
                    usuario_atual = partes[1]

            # Determina quem está executando o comando
            if texto.lower().startswith("login"):
                # Login: ainda não tem usuario_atual definido, passa endereço real
                nome_para_comando = None
                endereco_real = client_addr  # TUPLA REAL (ip, porta)
            else:
                # Outros comandos: precisa estar logado
                nome_para_comando = usuario_atual
                endereco_real = None

            # Se não está logado e não é login, erro
            if nome_para_comando is None and not texto.lower().startswith("login"):
                enviar_ack(sock, client_addr, seq)
                sessao["seq_esperado"] = 1 - sessao["seq_esperado"]
                enviar_pacote_rdt(client_addr, "ERRO: faça login primeiro")
                continue

            # Executa comando
            resposta = tratar_comando(texto, nome_para_comando, endereco_real)
            print(f"[PROCESSAR] Resposta: {resposta[:40]}")

            # Logout: limpa antes de enviar resposta
            if texto.lower().startswith("logout"):
                if usuario_atual and usuario_atual in usuarios_online:
                    with lock_usuarios:
                        if usuario_atual in usuarios_online:
                            del usuarios_online[usuario_atual]
                usuario_atual = None

            enviar_ack(sock, client_addr, seq)
            sessao["seq_esperado"] = 1 - sessao["seq_esperado"]

            if resposta is not None:
                enviar_pacote_rdt(client_addr, resposta)

            if texto.lower().startswith("logout"):
                sessao["ativa"] = False
                print(f"[PROCESSAR] Desconectado de {client_addr}")
                break
        else:
            ultimo_ack = 1 - sessao["seq_esperado"]
            print(f"[PROCESSAR] Pacote duplicado ({seq} != {sessao['seq_esperado']}), reenviando ACK {ultimo_ack}")
            enviar_ack(sock, client_addr, ultimo_ack)

    # LIMPEZA ao finalizar
    print(f"[SESSAO] Thread finalizada para {client_addr}")
    if usuario_atual and usuario_atual in usuarios_online:
        with lock_usuarios:
            if usuario_atual in usuarios_online:
                del usuarios_online[usuario_atual]
                print(f"[SESSAO] Removido {usuario_atual} de usuarios_online")
    if client_addr in clientes:
        del clientes[client_addr]
        print(f"[SESSAO] Removido {client_addr} de clientes")

def receber_pacotes(sock):
    """Loop principal do servidor (Despachante)."""
    while True:
        try:
            pacote, client_addr = sock.recvfrom(BUFFER_SIZE)
        except OSError:
            print("[SERVIDOR] Socket encerrado")
            break

        if simular_perda():
            print(f"[RECEBER] Pacote perdido (simulado) de {client_addr}")
            continue

        if client_addr not in clientes:
            criar_sessao_cliente(sock, client_addr)

        sessao = clientes.get(client_addr)
        if not sessao:
            continue

        if pacote.startswith(b'ACK:'):
            sessao["fila_acks"].put(pacote)
        else:
            sessao["fila_comandos"].put(pacote)

def cronometro_leiloes():
    """Thread em background que decrementa tempo dos leilões."""
    while True:
        time.sleep(1)
        if not leiloes_ativos:
            continue

        encerrados = []
        with lock_leiloes:
            for id_item, leilao in list(leiloes_ativos.items()):
                if not leilao.get("ativo", True):
                    continue
                tempo = leilao.get("tempo_restante")
                if tempo is None:
                    continue
                if tempo > 0:
                    leilao["tempo_restante"] = tempo - 1
                if leilao["tempo_restante"] <= 0:
                    leilao["ativo"] = False
                    encerrados.append((id_item, leilao))
                    print(f"[TIMER] Leilão encerrado para o item {id_item}")

        for id_item, leilao in encerrados:
            produto = leilao["produto"]
            vencedor = leilao.get("maior_lance", "Ninguém")
            preco = leilao["preco"]
            msg = f"LEILÃO ENCERRADO POR TEMPO! {produto} (ID {id_item}) - Vencedor: {vencedor} com R${preco}"
            broadcast(msg)


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor.bind((HOST, PORT))
    print(f"[SERVIDOR] AuctionCin operando em {HOST}:{PORT}")

    threading.Thread(target=receber_pacotes, args=(servidor,), daemon=True).start()
    threading.Thread(target=cronometro_leiloes, daemon=True).start()

    print("[SERVIDOR] Aguardando conexões...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SERVIDOR] Encerrando...")
    finally:
        servidor.close()

if __name__ == "__main__":
    main()
