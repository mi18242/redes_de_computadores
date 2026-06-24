# comandos.py

import time


# ==========================
# ESTADOS GLOBAIS
# ==========================

usuarios_online = {}

leiloes_ativos = {}

proximo_id = 1



# ==========================
# LOGIN
# ==========================

def fazer_login(nome, endereco):

    if nome in usuarios_online:
        return "ERRO: usuário já conectado"


    usuarios_online[nome] = endereco

    return "Você está online"



# ==========================
# LOGOUT
# ==========================

def fazer_logout(nome):

    if nome not in usuarios_online:
        return "ERRO: usuário não está online"


    del usuarios_online[nome]

    return "Logout realizado"



# ==========================
# CREATE
# ==========================

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

        "tempo": tempo,

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



# ==========================
# LIST
# ==========================

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
                f"\nTempo: {item['tempo_restante']}s"
                f"\n"
            )


    return resposta



# ==========================
# BID
# ==========================

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

        return (
            "ERRO: lance precisa "
            "ser maior que o atual"
        )



    item["preco"] = valor

    item["maior_lance"] = usuario
    
    item["lances"] += 1

    #encerra apos 5 lances
    if item["lances"] >= 5:
        item["ativo"] = False

    return (
        f"Lance aceito\n"
        f"Produto: {item['produto']}\n"
        f"Valor: R${valor}\n"
        f"Usuário: {usuario}"
    )



# ==========================
# INTERPRETADOR
# ==========================

def tratar_comando(mensagem, usuario):


    partes = mensagem.split()


    if len(partes) == 0:

        return "Comando vazio"



    comando = partes[0]



    if comando == "login":

        return fazer_login(
            partes[1],
            usuario
        )



    elif comando == "logout":

        return fazer_logout(usuario)



    elif comando == "create":

        return criar_leilao(
            partes[1],
            partes[2],
            partes[3]
        )



    elif comando == "list":

        return listar_leiloes()



    elif comando == "bid":

        return dar_lance(
            usuario,
            partes[1],
            partes[2]
        )



    else:

        return "Comando inválido"