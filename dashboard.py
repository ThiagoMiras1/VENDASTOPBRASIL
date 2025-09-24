import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import random
from faker import Faker

fake = Faker('pt_BR')

# ---------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------
st.set_page_config(
    page_title="🚀 Performance de Vendas – TOP BRASIL",
    layout="wide"
)

# ---------------------------
# COLUNAS PADRÃO
# ---------------------------
COLUNAS = ['Data','Nome do Cliente','Telefone','Veiculo','Placa','Plano',
           'Valor Adesao','Valor Mensalidade','Status Adesao','Status Mensalidade']

# ---------------------------
# FUNÇÃO PARA CARREGAR/CRIAR CSV E ADICIONAR CLIENTES FICTICIOS
# ---------------------------
def carregar_dados():
    arquivo = "vendas.csv"
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo, encoding="latin-1")
    else:
        df = pd.DataFrame(columns=COLUNAS)

    for col in COLUNAS:
        if col not in df.columns:
            df[col] = None

    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df['Valor Adesao'] = pd.to_numeric(df['Valor Adesao'], errors='coerce')
    df['Valor Mensalidade'] = pd.to_numeric(df['Valor Mensalidade'], errors='coerce')

    # Adicionar 10 clientes fictícios se ainda não existirem
    if not df['Nome do Cliente'].str.contains("Teste", na=False).any():
        planos = ["Plano Essencial", "Plano Plus", "Plano Premium", "Plano Moto"]
        veiculos = ["Carro A", "Carro B", "Carro C", "Carro D", "Moto A", "Moto B"]
        novos_clientes = []
        for i in range(10):
            novos_clientes.append({
                'Data': datetime(2025, 9, i+1),
                'Nome do Cliente': f"{fake.first_name()} Teste {i+1}",
                'Telefone': fake.phone_number(),
                'Veiculo': random.choice(veiculos),
                'Placa': fake.bothify(text='???####'),
                'Plano': random.choice(planos),
                'Valor Adesao': round(random.uniform(80, 150), 2),
                'Valor Mensalidade': round(random.uniform(40, 70), 2),
                'Status Adesao': random.choice(["Pago", "Pendente"]),
                'Status Mensalidade': random.choice(["Pago", "Pendente"])
            })
        df = pd.concat([df, pd.DataFrame(novos_clientes)], ignore_index=True)
        df.to_csv(arquivo, index=False, encoding="latin-1")

    return df[COLUNAS]

# Inicializa session_state
if "df" not in st.session_state:
    st.session_state.df = carregar_dados()
df = st.session_state.df

# ---------------------------
# FUNÇÃO PARA CRIAR CARDS MODERNOS ESTILO POWER BI
# ---------------------------
def criar_card_moderno(titulo, valor, cor_fundo="#1f77b4"):
    st.markdown(f"""
        <div style="
            background-color:{cor_fundo};
            color:white;
            padding:20px;
            border-radius:12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            text-align:center;
            min-height:100px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            margin-bottom:10px;">
            <span style='font-size:26px; font-weight:bold;'>{valor}</span>
            <span style='font-size:14px; opacity:0.8;'>{titulo}</span>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------
# MENU SUPERIOR EM ABAS
# ---------------------------
tabs = st.tabs(["VISÃO GERAL", "CADASTRO", "FILTRO", "EDITAR"])

# ---------------------------
# VISÃO GERAL
# ---------------------------
with tabs[0]:
    st.subheader("🚀 Performance de Vendas – TOP BRASIL")

    if df.empty:
        st.warning("Nenhuma venda cadastrada ainda.")
    else:
        total_adesao = df['Valor Adesao'].sum()
        total_mensalidade = df['Valor Mensalidade'].sum()
        total_clientes = len(df)
        
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        novos_clientes = df[(df['Data'].dt.month == mes_atual) & (df['Data'].dt.year == ano_atual)]
        qtd_novos_clientes = len(novos_clientes)
        
        clientes_mensalidade_paga = df[df['Status Mensalidade'] == 'Pago']
        qtd_clientes_mensalidade_paga = len(clientes_mensalidade_paga)

        # PRIMEIRA LINHA - Valores monetários
        kpi1, kpi2 = st.columns(2, gap="medium")
        with kpi1:
            criar_card_moderno("Total Arrecadado (R$)", f"R$ {total_adesao:,.2f}", "#FF6F61")
        with kpi2:
            criar_card_moderno("Receita Mensal Recorrente (MRR) (R$)", f"R$ {total_mensalidade:,.2f}", "#4CAF50")

        # SEGUNDA LINHA - Contagem de clientes
        kpi3, kpi4, kpi5 = st.columns(3, gap="medium")
        with kpi3:
            criar_card_moderno("Total de Clientes", f"{total_clientes}", "#2196F3")
        with kpi4:
            criar_card_moderno("Novos Clientes no Mês", f"{qtd_novos_clientes}", "#FFC107")
        with kpi5:
            criar_card_moderno("Clientes com Mensalidade Paga", f"{qtd_clientes_mensalidade_paga}", "#9C27B0")

        # GRÁFICO: Clientes com Adesão Paga/Pendente
        st.subheader("Gráfico de Clientes com Adesão Pago/Pendente")
        adesao_status = df['Status Adesao'].value_counts().reset_index()
        adesao_status.columns = ['Status Adesao', 'Quantidade']
        fig = px.pie(
            adesao_status,
            names='Status Adesao',
            values='Quantidade',
            color='Status Adesao',
            color_discrete_map={'Pago':'#4CAF50','Pendente':'#FF6F61'},
            hole=0.3,
            title="Clientes por Status de Adesão"
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# CADASTRO
# ---------------------------
with tabs[1]:
    st.subheader("📂 Cadastro de Vendas")
    with st.form("nova_venda_form", clear_on_submit=True):
        data_venda = st.date_input("Data da Venda", datetime.now())
        nome_cliente = st.text_input("Nome do Cliente")
        telefone_cliente = st.text_input("Telefone")
        veiculo = st.text_input("Veículo")
        placa = st.text_input("Placa")
        plano = st.selectbox("Plano Contratado", ["Plano Essencial", "Plano Plus", "Plano Premium", "Plano Moto"])
        valor_adesao = st.number_input("Valor da Adesão (R$)", min_value=0.0, format="%.2f")
        valor_mensalidade = st.number_input("Valor da Mensalidade (R$)", min_value=0.0, format="%.2f")
        status_adesao = st.selectbox("Status Adesao", ["Pago", "Pendente"])
        status_mensalidade = st.selectbox("Status Mensalidade", ["Pago", "Pendente"])
        submitted = st.form_submit_button("Adicionar Venda")
        if submitted:
            nova_venda = pd.DataFrame([{
                'Data': data_venda,
                'Nome do Cliente': nome_cliente,
                'Telefone': telefone_cliente,
                'Veiculo': veiculo,
                'Placa': placa,
                'Plano': plano,
                'Valor Adesao': valor_adesao,
                'Valor Mensalidade': valor_mensalidade,
                'Status Adesao': status_adesao,
                'Status Mensalidade': status_mensalidade
            }])
            st.session_state.df = pd.concat([st.session_state.df, nova_venda], ignore_index=True)
            st.session_state.df.to_csv("vendas.csv", index=False, encoding="latin-1")
            st.success("Venda adicionada com sucesso!")
            st.stop()  # força atualização sem experimental_rerun

# ---------------------------
# FILTRO
# ---------------------------
with tabs[2]:
    st.subheader("🔍 Filtros de Visualização e Gráficos")
    status_dashboard = st.selectbox("Filtrar por Status Adesão", ["Todos", "Pago", "Pendente"])
    plano_dashboard = st.selectbox("Filtrar por Plano", ["Todos", "Plano Essencial", "Plano Plus", "Plano Premium", "Plano Moto"])
    cliente_filtro = st.text_input("Buscar por Nome do Cliente")

    aplicar_filtro = st.button("Aplicar Filtros")

    if aplicar_filtro:
        df_filtrado = st.session_state.df.copy()
        if status_dashboard != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Status Adesao"] == status_dashboard]
        if plano_dashboard != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Plano'] == plano_dashboard]
        if cliente_filtro:
            df_filtrado = df_filtrado[df_filtrado['Nome do Cliente'].str.contains(cliente_filtro, case=False, na=False)]

        st.subheader("Tabela Filtrada de Vendas")
        st.dataframe(df_filtrado.style.set_table_attributes("style='width:100%'"), use_container_width=True)

        st.subheader("Gráfico de Clientes com Adesão Pago/Pendente")
        adesao_status = df_filtrado['Status Adesao'].value_counts().reset_index()
        adesao_status.columns = ['Status Adesao', 'Quantidade']
        fig = px.pie(
            adesao_status,
            names='Status Adesao',
            values='Quantidade',
            color='Status Adesao',
            color_discrete_map={'Pago':'#4CAF50','Pendente':'#FF6F61'},
            hole=0.3,
            title="Clientes por Status de Adesão"
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# EDITAR
# ---------------------------
with tabs[3]:
    st.subheader("✏️ Editar ou Excluir Clientes")

    filtro_nome = st.text_input("Buscar por Nome do Cliente ou Placa", key="filtro_editar")
    df_editavel = st.session_state.df.copy()

    if filtro_nome:
        df_editavel = df_editavel[
            df_editavel['Nome do Cliente'].str.contains(filtro_nome, case=False, na=False) |
            df_editavel['Placa'].str.contains(filtro_nome, case=False, na=False)
        ]

    if df_editavel.empty:
        st.warning("Nenhum cliente encontrado.")
    else:
        df_editavel.insert(0, "Selecionar", False)
        df_editado = st.data_editor(
            df_editavel,
            width='stretch',
            hide_index=True,
            column_config={
                "Selecionar": st.column_config.CheckboxColumn("Selecionar", help="Marque para selecionar o cliente"),
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Valor Adesao": st.column_config.NumberColumn("Valor Adesão (R$)", format="R$ %.2f"),
                "Valor Mensalidade": st.column_config.NumberColumn("Valor Mensalidade (R$)", format="R$ %.2f"),
            },
            disabled=[c for c in df_editavel.columns if c != "Selecionar"]
        )

        selecionados = df_editado[df_editado["Selecionar"] == True]

        if not selecionados.empty:
            col_excluir, col_editar = st.columns(2)
            with col_excluir:
                if st.button("❌ Excluir Clientes Selecionados"):
                    idx_para_excluir = selecionados.index
                    st.session_state.df.drop(idx_para_excluir, inplace=True)
                    st.session_state.df.reset_index(drop=True, inplace=True)
                    st.session_state.df.to_csv("vendas.csv", index=False, encoding="latin-1")
                    st.success("Clientes excluídos com sucesso!")
                    st.stop()

            with col_editar:
                for idx in selecionados.index:
                    cliente = st.session_state.df.loc[idx]
                    st.sidebar.subheader(f"Editar Cliente: {cliente['Nome do Cliente']}")
                    novo_nome = st.sidebar.text_input("Nome do Cliente", cliente['Nome do Cliente'], key=f"nome_{idx}")
                    novo_telefone = st.sidebar.text_input("Telefone", cliente['Telefone'], key=f"tel_{idx}")
                    novo_veiculo = st.sidebar.text_input("Veículo", cliente['Veiculo'], key=f"veic_{idx}")
                    nova_placa = st.sidebar.text_input("Placa", cliente['Placa'], key=f"placa_{idx}")
                    novo_plano = st.sidebar.selectbox(
                        "Plano Contratado",
                        ["Plano Essencial","Plano Plus","Plano Premium","Plano Moto"],
                        index=["Plano Essencial","Plano Plus","Plano Premium","Plano Moto"].index(cliente['Plano']),
                        key=f"plano_{idx}"
                    )
                    novo_valor_adesao = st.sidebar.number_input(
                        "Valor da Adesão (R$)",
                        value=float(cliente['Valor Adesao']) if pd.notnull(cliente['Valor Adesao']) else 0.0,
                        key=f"vadesao_{idx}"
                    )
                    novo_valor_mensalidade = st.sidebar.number_input(
                        "Valor da Mensalidade (R$)",
                        value=float(cliente['Valor Mensalidade']) if pd.notnull(cliente['Valor Mensalidade']) else 0.0,
                        key=f"vmen_{idx}"
                    )
                    novo_status_adesao = st.sidebar.selectbox(
                        "Status Adesao", ["Pago","Pendente"],
                        index=["Pago","Pendente"].index(cliente['Status Adesao']),
                        key=f"sadesao_{idx}"
                    )
                    novo_status_mensalidade = st.sidebar.selectbox(
                        "Status Mensalidade", ["Pago","Pendente"],
                        index=["Pago","Pendente"].index(cliente['Status Mensalidade']),
                        key=f"smen_{idx}"
                    )

                    if st.sidebar.button("💾 Salvar Alterações", key=f"save_{idx}"):
                        st.session_state.df.loc[idx] = [
                            cliente['Data'], novo_nome, novo_telefone, novo_veiculo, nova_placa,
                            novo_plano, novo_valor_adesao, novo_valor_mensalidade,
                            novo_status_adesao, novo_status_mensalidade
                        ]
                        st.session_state.df.to_csv("vendas.csv", index=False, encoding="latin-1")
                        st.success(f"Cliente {novo_nome} atualizado com sucesso!")
                        st.stop()
