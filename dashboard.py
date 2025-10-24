import streamlit as st
import pandas as pd
from datetime import datetime
import os
import shutil
import sys
import re
from pathlib import Path
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# ---------------------------
# SISTEMA DE USUÁRIOS
# ---------------------------
USUARIOS = {
    "admin": {"senha": "admin123", "perfil": "Admin", "nome": "Administrador"},
    "vendedor": {"senha": "venda123", "perfil": "Vendedor", "nome": "Vendedor"},
    "gerente": {"senha": "gerente123", "perfil": "Gerente", "nome": "Gerente"},
    "visualizador": {"senha": "visual123", "perfil": "Visualizador", "nome": "Visualizador"}
}

def verificar_login(usuario, senha):
    """Verifica credenciais do usuário."""
    if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
        return True, USUARIOS[usuario]["perfil"], USUARIOS[usuario]["nome"]
    return False, None, None

def tem_permissao(acao):
    """Verifica se o usuário tem permissão para executar a ação."""
    if "user_perfil" not in st.session_state:
        return False
    
    perfil = st.session_state.user_perfil
    
    # Admin pode tudo
    if perfil == "Admin":
        return True
    
    # Gerente pode tudo exceto não pode editar configurações
    if perfil == "Gerente":
        return acao != "config"
    
    # Vendedor pode cadastrar e visualizar
    if perfil == "Vendedor":
        return acao in ["cadastrar", "visualizar", "filtrar"]
    
    # Visualizador só pode visualizar
    if perfil == "Visualizador":
        return acao == "visualizar"
    
    return False

# ---------------------------
# FUNÇÕES AUXILIARES
# ---------------------------
def format_brl(valor):
    """Formata valor monetário no padrão brasileiro."""
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def normaliza_placa(placa):
    """Remove caracteres especiais da placa."""
    return re.sub(r'[^A-Z0-9]', '', str(placa).upper())

def placa_valida(placa):
    """Valida formato de placa brasileira (padrão antigo e Mercosul)."""
    p = normaliza_placa(placa)
    return bool(re.fullmatch(r'[A-Z]{3}\d{4}', p) or re.fullmatch(r'[A-Z]{3}\d[A-Z]\d{2}', p))

def telefone_valido(telefone):
    """Valida se telefone tem 10 ou 11 dígitos."""
    digits = re.sub(r'\D', '', str(telefone))
    return len(digits) in (10, 11)

# Helper to find resource paths when app is frozen into an executable
def resource_path(relative_path: str) -> str:
    """Return the path to a resource, works for dev and for PyInstaller bundle.

    When frozen, PyInstaller extracts files to _MEIPASS; otherwise use repo path.
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return str(base_path / relative_path)

# ---------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------
st.set_page_config(
    page_title="🚀 Performance de Vendas – TOP BRASIL",
    page_icon="topbrasil.png",
    layout="wide"
)

# ---------------------------
# COLUNAS PADRÃO
# ---------------------------
COLUNAS = ['Data','Nome do Cliente','Telefone','Veiculo','Modelo do Veículo','Placa','Plano',
           'Valor Adesao','Valor Mensalidade','Status Adesao','Status Mensalidade']

# ---------------------------
# FUNÇÃO PARA CARREGAR/CRIAR CSV E ADICIONAR CLIENTES FICTICIOS
# ---------------------------
def carregar_dados():
    # Try to load from user's Documents folder first (where saves go)
    arquivo_usuario = DATA_DIR / "vendas.csv"
    
    if arquivo_usuario.exists():
        df = pd.read_csv(str(arquivo_usuario), encoding="latin-1")
    else:
        # Fallback: try bundled vendas.csv (initial/template)
        arquivo_bundle = resource_path("vendas.csv")
        if os.path.exists(arquivo_bundle):
            df = pd.read_csv(arquivo_bundle, encoding="latin-1")
        else:
            df = pd.DataFrame(columns=COLUNAS)

    for col in COLUNAS:
        if col not in df.columns:
            df[col] = None

    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df['Valor Adesao'] = pd.to_numeric(df['Valor Adesao'], errors='coerce')
    df['Valor Mensalidade'] = pd.to_numeric(df['Valor Mensalidade'], errors='coerce')
    
    # Garantir que todas as colunas de texto sejam do tipo string (exceto Data)
    colunas_texto = ['Nome do Cliente', 'Telefone', 'Veiculo', 'Modelo do Veículo', 'Placa', 'Plano', 'Status Adesao', 'Status Mensalidade']
    for col in colunas_texto:
        df[col] = df[col].astype(str)

    # App inicia sempre vazio - sem dados de teste

    return df[COLUNAS]


# ---------------------------
# BACKUP AUTOMÁTICO ANTES DE SALVAR
# ---------------------------
# Data should be stored in user's Documents folder (always writable)
# This allows the app to run from Program Files without permission issues
def get_data_dir():
    """Returns a writable directory for application data in user's Documents folder."""
    docs = Path.home() / "Documents" / "VendasTopBrasil"
    docs.mkdir(parents=True, exist_ok=True)
    return docs

DATA_DIR = get_data_dir()
BACKUP_DIR = DATA_DIR / "backups"

def ensure_backup_dir():
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def backup_file(path: str):
    p = Path(path)
    if p.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = BACKUP_DIR / f"{p.stem}_{ts}{p.suffix}"
        try:
            shutil.copy2(p, dest)
        except Exception:
            pass

def save_vendas(df_to_save: pd.DataFrame):
    """Faz backup do arquivo vendas.csv (se existir) e salva o DataFrame no CSV.
    
    Saves to user's Documents folder which is always writable.
    """
    ensure_backup_dir()
    target = DATA_DIR / "vendas.csv"
    backup_file(str(target))
    df_to_save.to_csv(str(target), index=False, encoding="latin-1")

def gerar_csv(df_filtrado: pd.DataFrame) -> bytes:
    """Gera arquivo CSV do DataFrame filtrado."""
    return df_filtrado.to_csv(index=False, encoding="latin-1").encode("latin-1")

def gerar_excel(df_filtrado: pd.DataFrame) -> BytesIO:
    """Gera arquivo Excel do DataFrame filtrado."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name='Vendas')
    output.seek(0)
    return output

def gerar_pdf(df_filtrado: pd.DataFrame) -> BytesIO:
    """Gera arquivo PDF do DataFrame filtrado."""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    elements = []
    
    styles = getSampleStyleSheet()
    title = Paragraph("<b>Relatório de Vendas - TOP BRASIL</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # Preparar dados para tabela
    data = [df_filtrado.columns.tolist()]
    for _, row in df_filtrado.iterrows():
        row_data = []
        for val in row:
            if pd.isna(val):
                row_data.append('')
            elif isinstance(val, (int, float)):
                row_data.append(f'{val:.2f}' if isinstance(val, float) else str(val))
            else:
                row_data.append(str(val))
        data.append(row_data)
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    output.seek(0)
    return output

# ---------------------------
# CONTROLE DE SESSÃO E LOGIN
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_nome" not in st.session_state:
    st.session_state.user_nome = ""
if "user_perfil" not in st.session_state:
    st.session_state.user_perfil = ""
if "user_login" not in st.session_state:
    st.session_state.user_login = ""

# TELA DE LOGIN
if not st.session_state.logged_in:
    st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <h1>🚀 TOP BRASIL</h1>
            <h3>Sistema de Gestão de Vendas</h3>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        usuario = st.text_input("👤 Usuário", key="login_user")
        senha = st.text_input("🔑 Senha", type="password", key="login_pass")
        
        if st.button("Entrar", use_container_width=True):
            sucesso, perfil, nome = verificar_login(usuario, senha)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.user_nome = nome
                st.session_state.user_perfil = perfil
                st.session_state.user_login = usuario
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos!")
        
        st.markdown("---")
        st.info("""
        **👥 Usuários de Teste:**
        - `admin` / `admin123` (Acesso Total)
        - `gerente` / `gerente123` (Gerenciar Vendas)
        - `vendedor` / `venda123` (Cadastrar e Visualizar)
        - `visualizador` / `visual123` (Apenas Visualizar)
        """)
    st.stop()

# Inicializa session_state
if "df" not in st.session_state:
    st.session_state.df = carregar_dados()
df = st.session_state.df

# Flag para distinguir submissão por clique do botão vs Enter
if "submit_venda_clicked" not in st.session_state:
    st.session_state.submit_venda_clicked = False

# BARRA SUPERIOR COM INFO DO USUÁRIO
col_user, col_logout = st.columns([4, 1])
with col_user:
    st.markdown(f"👤 **{st.session_state.user_nome}** ({st.session_state.user_perfil})")
with col_logout:
    if st.button("🚪 Sair"):
        st.session_state.logged_in = False
        st.session_state.user_nome = ""
        st.session_state.user_perfil = ""
        st.session_state.user_login = ""
        st.rerun()

st.markdown("---")

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
        
        # Calcular valor das adesões pagas
        adesoes_pagas = df[df['Status Adesao'] == 'Pago']
        valor_adesoes_pagas = adesoes_pagas['Valor Adesao'].sum()
        qtd_clientes_adesao_paga = len(adesoes_pagas)
        
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        novos_clientes = df[(df['Data'].dt.month == mes_atual) & (df['Data'].dt.year == ano_atual)]
        qtd_novos_clientes = len(novos_clientes)

        # PRIMEIRA LINHA - Valores monetários
        kpi1, kpi2 = st.columns(2, gap="medium")
        with kpi1:
            criar_card_moderno("Total de Adesões", format_brl(total_adesao), "#FF6F61")
        with kpi2:
            criar_card_moderno("Valor das Adesões Pagas", format_brl(valor_adesoes_pagas), "#4CAF50")

        # SEGUNDA LINHA - Contagem de clientes
        kpi3, kpi4, kpi5 = st.columns(3, gap="medium")
        with kpi3:
            criar_card_moderno("Total de Clientes", f"{total_clientes}", "#2196F3")
        with kpi4:
            criar_card_moderno("Novos Clientes no Mês", f"{qtd_novos_clientes}", "#FFC107")
        with kpi5:
            criar_card_moderno("Clientes com Adesão Paga", f"{qtd_clientes_adesao_paga}", "#9C27B0")

        # RESUMO ESTATÍSTICO
        st.subheader("📊 Resumo Estatístico")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Clientes com Adesão Paga", 
                     len(df[df['Status Adesao'] == 'Pago']),
                     f"{len(df[df['Status Adesao'] == 'Pago'])/len(df)*100:.1f}%")
        
        with col2:
            st.metric("Clientes com Adesão Pendente", 
                     len(df[df['Status Adesao'] == 'Pendente']),
                     f"{len(df[df['Status Adesao'] == 'Pendente'])/len(df)*100:.1f}%")
        
        # GRÁFICOS
        st.subheader("📈 Análise de Vendas")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.markdown("**📊 Vendas por Mês**")
            df_temporal = df.dropna(subset=['Data']).copy()
            df_temporal['Mes'] = df_temporal['Data'].dt.to_period('M').dt.to_timestamp()
            vendas_mes = df_temporal.groupby('Mes').size()
            
            # Criar DataFrame com nomes dos meses em português
            vendas_mes_df = pd.DataFrame(vendas_mes)
            vendas_mes_df.index = vendas_mes_df.index.strftime('%b/%Y')
            vendas_mes_df.index = vendas_mes_df.index.str.replace('Jan', 'Jan')\
                .str.replace('Feb', 'Fev').str.replace('Mar', 'Mar')\
                .str.replace('Apr', 'Abr').str.replace('May', 'Mai')\
                .str.replace('Jun', 'Jun').str.replace('Jul', 'Jul')\
                .str.replace('Aug', 'Ago').str.replace('Sep', 'Set')\
                .str.replace('Oct', 'Out').str.replace('Nov', 'Nov')\
                .str.replace('Dec', 'Dez')
            
            st.line_chart(vendas_mes_df)
            st.caption(f"📈 Total: {vendas_mes.sum()} vendas | Média: {vendas_mes.mean():.1f}/mês")
        
        with col_graf2:
            st.markdown("**💰 Receita de Adesões por Mês**")
            receita_mes = df_temporal.groupby('Mes')['Valor Adesao'].sum()
            
            # Criar DataFrame com nomes dos meses em português
            receita_mes_df = pd.DataFrame(receita_mes)
            receita_mes_df.index = receita_mes_df.index.strftime('%b/%Y')
            receita_mes_df.index = receita_mes_df.index.str.replace('Jan', 'Jan')\
                .str.replace('Feb', 'Fev').str.replace('Mar', 'Mar')\
                .str.replace('Apr', 'Abr').str.replace('May', 'Mai')\
                .str.replace('Jun', 'Jun').str.replace('Jul', 'Jul')\
                .str.replace('Aug', 'Ago').str.replace('Sep', 'Set')\
                .str.replace('Oct', 'Out').str.replace('Nov', 'Nov')\
                .str.replace('Dec', 'Dez')
            
            st.bar_chart(receita_mes_df)
            st.caption(f"💵 Total: {format_brl(receita_mes.sum())} | Média: {format_brl(receita_mes.mean())}/mês")
        
        # DASHBOARD EXECUTIVO - Para impressionar clientes
        st.subheader("🎯 Dashboard Executivo")
        
        col_exec1, col_exec2, col_exec3 = st.columns(3)
        
        with col_exec1:
            # Taxa de conversão
            taxa_conversao = (len(df[df['Status Adesao'] == 'Pago']) / len(df) * 100) if len(df) > 0 else 0
            st.metric("Taxa de Conversão", f"{taxa_conversao:.1f}%", 
                     delta="Meta: 80%", delta_color="normal")
        
        with col_exec2:
            # Ticket médio
            ticket_medio = df[df['Status Adesao'] == 'Pago']['Valor Adesao'].mean()
            st.metric("Ticket Médio (Pagas)", format_brl(ticket_medio) if pd.notnull(ticket_medio) else "R$ 0,00")
        
        with col_exec3:
            # Pendências a receber
            pendencias = df[df['Status Adesao'] == 'Pendente']['Valor Adesao'].sum()
            st.metric("Pendências a Receber", format_brl(pendencias),
                     delta=f"{len(df[df['Status Adesao'] == 'Pendente'])} cliente(s)")
        
        # Top 5 Planos
        st.markdown("**🏆 Top 5 Planos Mais Vendidos**")
        top_planos = df.groupby('Plano').agg({
            'Plano': 'count',
            'Valor Adesao': 'sum'
        }).rename(columns={'Plano': 'Vendas', 'Valor Adesao': 'Receita'})
        top_planos = top_planos.sort_values('Receita', ascending=False).head(5)
        top_planos['Receita'] = top_planos['Receita'].apply(format_brl)
        st.dataframe(top_planos, use_container_width=True)

# ---------------------------
# CADASTRO
# ---------------------------
with tabs[1]:
    st.subheader("📂 Cadastro de Vendas")
    
    if not tem_permissao("cadastrar"):
        st.warning("⚠️ Você não tem permissão para cadastrar vendas. Entre em contato com o administrador.")
        st.stop()
    
    with st.form("nova_venda_form", clear_on_submit=True):
        data_venda = st.date_input("Data da Venda", datetime.now())
        nome_cliente = st.text_input("Nome do Cliente")
        telefone_cliente = st.text_input("Telefone")
        veiculo = st.text_input("Veículo")
        modelo_veiculo = st.text_input("Modelo do Veículo")
        placa = st.text_input("Placa")
        plano = st.selectbox("Plano Contratado", ["GOLD", "PLATINUM", "BLACK", "GOLD ADICIONAL"])
        valor_adesao = st.number_input("Valor da Adesão (R$)", min_value=0.0, format="%.2f")
        valor_mensalidade = st.number_input("Valor da Mensalidade (R$)", min_value=0.0, format="%.2f")
        st.caption("Atenção: o valor da mensalidade é apenas para consulta e não gera cobranças automáticas.")
        confirmar_mensalidade = st.checkbox("Confirmo que o Valor da Mensalidade é apenas para consulta", value=False)
        status_adesao = st.selectbox("Status Adesao", ["Pago", "Pendente"])
        # Usamos on_click para marcar que o botão foi clicado explicitamente.
        submitted = st.form_submit_button("Adicionar Venda", on_click=lambda: st.session_state.__setitem__('submit_venda_clicked', True))
        if submitted:
            # Se o formulário foi submetido por Enter, submit_venda_clicked ficará False.
            if st.session_state.get('submit_venda_clicked', False):
                if not confirmar_mensalidade:
                    st.warning("Para adicionar a venda, confirme que o valor da mensalidade é apenas para consulta.")
                    st.session_state['submit_venda_clicked'] = False
                    st.stop()
                
                # VALIDAÇÕES
                erros = []
                if not nome_cliente.strip():
                    erros.append("❌ Nome do cliente é obrigatório.")
                if not telefone_valido(telefone_cliente):
                    erros.append("❌ Telefone inválido (use 10-11 dígitos, ex: (11) 99999-9999).")
                if not placa_valida(placa):
                    erros.append("❌ Placa inválida (ex: ABC-1234 ou ABC1D23).")
                if status_adesao == "Pago" and valor_adesao <= 0:
                    erros.append("❌ Valor da adesão deve ser maior que zero para status Pago.")
                
                # Verificar duplicatas por placa e data
                placa_norm = normaliza_placa(placa)
                if not st.session_state.df.empty:
                    ja_existe = (
                        (st.session_state.df['Data'].dt.date == data_venda) &
                        (st.session_state.df['Placa'].apply(normaliza_placa) == placa_norm)
                    )
                    if ja_existe.any():
                        erros.append("❌ Já existe uma venda para esta placa nesta data.")
                
                if erros:
                    for erro in erros:
                        st.error(erro)
                    st.session_state['submit_venda_clicked'] = False
                    st.stop()
                
                # Normalizar dados antes de salvar
                telefone_limpo = re.sub(r'\D', '', str(telefone_cliente))
                nome_normalizado = nome_cliente.strip().title()
                
                nova_venda = pd.DataFrame([{
                    'Data': data_venda,
                    'Nome do Cliente': nome_normalizado,
                    'Telefone': telefone_limpo,
                    'Veiculo': veiculo,
                    'Modelo do Veículo': modelo_veiculo,
                    'Placa': placa_norm,
                    'Plano': plano,
                    'Valor Adesao': valor_adesao,
                    'Valor Mensalidade': valor_mensalidade,
                    'Status Adesao': status_adesao,
                    'Status Mensalidade': ''
                }])
                st.session_state.df = pd.concat([st.session_state.df, nova_venda], ignore_index=True)
                # Garantir que a coluna Data seja datetime antes de salvar
                st.session_state.df['Data'] = pd.to_datetime(st.session_state.df['Data'], errors='coerce')
                save_vendas(st.session_state.df)
                st.success("✅ Venda adicionada com sucesso!")
                # reset flag
                st.session_state['submit_venda_clicked'] = False
                st.rerun()
            else:
                # Ignorar submissão via Enter
                st.info("Por favor, clique no botão 'Adicionar Venda' para salvar o cadastro.")
                # garantir flag em False
                st.session_state['submit_venda_clicked'] = False

# ---------------------------
# FILTRO
# ---------------------------
with tabs[2]:
    st.subheader("🔍 Filtros de Visualização e Gráficos")
    
    # Período único
    if not st.session_state.df.empty:
        min_dt = st.session_state.df['Data'].min()
        max_dt = st.session_state.df['Data'].max()
        default_periodo = (
            min_dt.date() if pd.notnull(min_dt) else datetime.now().date(),
            max_dt.date() if pd.notnull(max_dt) else datetime.now().date()
        )
    else:
        default_periodo = (datetime.now().date(), datetime.now().date())
    
    periodo = st.date_input("📅 Período", value=default_periodo, help="Selecione o período de vendas")
    if len(periodo) == 2:
        data_inicio, data_fim = periodo
    else:
        data_inicio = data_fim = periodo[0] if periodo else None
    
    status_dashboard = st.selectbox("Filtrar por Status Adesão", ["Todos", "Pago", "Pendente"])
    plano_dashboard = st.selectbox("Filtrar por Plano", ["Todos", "GOLD", "PLATINUM", "BLACK", "GOLD ADICIONAL"])
    cliente_filtro = st.text_input("Buscar por Nome do Cliente")

    col_aplicar, col_limpar = st.columns([1, 1])
    with col_aplicar:
        aplicar_filtro = st.button("🔍 Aplicar Filtros", use_container_width=True)
    with col_limpar:
        if st.button("🔄 Limpar Filtros", use_container_width=True):
            st.rerun()

    if aplicar_filtro:
        df_filtrado = st.session_state.df.copy()
        
        if data_inicio is not None:
            df_filtrado = df_filtrado[df_filtrado['Data'] >= pd.to_datetime(data_inicio)]
        if data_fim is not None:
            df_filtrado = df_filtrado[df_filtrado['Data'] <= pd.to_datetime(data_fim)]
        
        if status_dashboard != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Status Adesao"] == status_dashboard]
        if plano_dashboard != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Plano'] == plano_dashboard]
        if cliente_filtro:
            df_filtrado = df_filtrado[df_filtrado['Nome do Cliente'].str.contains(cliente_filtro, case=False, na=False)]

        st.subheader("Tabela Filtrada de Vendas")
        st.caption(f"📊 {len(df_filtrado)} registro(s) encontrado(s)")
        st.dataframe(df_filtrado.style.set_table_attributes("style='width:100%'"), width='stretch')

        # BOTÕES DE EXPORTAÇÃO
        col_csv, col_excel, col_pdf = st.columns(3)
        with col_csv:
            csv_data = gerar_csv(df_filtrado)
            st.download_button(
                label="📄 Baixar CSV",
                data=csv_data,
                file_name=f"vendas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_excel:
            excel_data = gerar_excel(df_filtrado)
            st.download_button(
                label="📥 Baixar Excel",
                data=excel_data,
                file_name=f"vendas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_pdf:
            pdf_data = gerar_pdf(df_filtrado)
            st.download_button(
                label="📑 Baixar PDF",
                data=pdf_data,
                file_name=f"vendas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        # RESUMO ESTATÍSTICO FILTRADO
        st.subheader("📊 Resumo Estatístico Filtrado")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Clientes com Adesão Paga", 
                     len(df_filtrado[df_filtrado['Status Adesao'] == 'Pago']),
                     f"{len(df_filtrado[df_filtrado['Status Adesao'] == 'Pago'])/len(df_filtrado)*100:.1f}%" if len(df_filtrado) > 0 else "0%")
        
        with col2:
            st.metric("Clientes com Adesão Pendente", 
                     len(df_filtrado[df_filtrado['Status Adesao'] == 'Pendente']),
                     f"{len(df_filtrado[df_filtrado['Status Adesao'] == 'Pendente'])/len(df_filtrado)*100:.1f}%" if len(df_filtrado) > 0 else "0%")

# ---------------------------
# EDITAR
# ---------------------------
with tabs[3]:
    st.subheader("✏️ Editar ou Excluir Clientes")
    
    if not tem_permissao("cadastrar"):
        st.warning("⚠️ Você não tem permissão para editar ou excluir vendas. Entre em contato com o administrador.")
        st.stop()

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
            if len(selecionados) > 1:
                st.warning("⚠️ Edite um cliente por vez para evitar conflitos. Para excluir múltiplos clientes, use o botão de exclusão.")
            
            col_excluir, col_editar = st.columns(2)
            with col_excluir:
                st.markdown(f"**{len(selecionados)} cliente(s) selecionado(s)**")
                confirmar_exclusao = st.checkbox("Confirmo que desejo excluir os clientes selecionados", key="confirmar_exclusao")
                if st.button("❌ Excluir Clientes Selecionados", disabled=not confirmar_exclusao):
                    # Obter os índices originais dos clientes selecionados
                    idx_originais = []
                    for idx_filtrado in selecionados.index:
                        # Encontrar o índice original no DataFrame principal
                        nome_cliente = df_editado.loc[idx_filtrado, 'Nome do Cliente']
                        placa_cliente = df_editado.loc[idx_filtrado, 'Placa']
                        
                        # Buscar no DataFrame original
                        mask = (st.session_state.df['Nome do Cliente'] == nome_cliente) & (st.session_state.df['Placa'] == placa_cliente)
                        idx_original = st.session_state.df[mask].index[0]
                        idx_originais.append(idx_original)
                    
                    # Excluir usando os índices originais
                    st.session_state.df.drop(idx_originais, inplace=True)
                    st.session_state.df.reset_index(drop=True, inplace=True)
                    save_vendas(st.session_state.df)
                    st.success(f"✅ {len(idx_originais)} cliente(s) excluído(s) com sucesso!")
                    st.rerun()

            with col_editar:
                for idx in selecionados.index:
                    cliente = st.session_state.df.loc[idx]
                    st.sidebar.subheader(f"Editar Cliente: {cliente['Nome do Cliente']}")
                    novo_nome = st.sidebar.text_input("Nome do Cliente", cliente['Nome do Cliente'], key=f"nome_{idx}")
                    novo_telefone = st.sidebar.text_input("Telefone", cliente['Telefone'], key=f"tel_{idx}")
                    novo_veiculo = st.sidebar.text_input("Veículo", cliente['Veiculo'], key=f"veic_{idx}")
                    novo_modelo = st.sidebar.text_input("Modelo do Veículo", cliente.get('Modelo do Veículo', ''), key=f"modelo_{idx}")
                    nova_placa = st.sidebar.text_input("Placa", cliente['Placa'], key=f"placa_{idx}")
                    novo_plano = st.sidebar.selectbox(
                        "Plano Contratado",
                        ["GOLD","PLATINUM","BLACK","GOLD ADICIONAL"],
                        index=["GOLD","PLATINUM","BLACK","GOLD ADICIONAL"].index(cliente['Plano']),
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

                    if st.sidebar.button("💾 Salvar Alterações", key=f"save_{idx}"):
                        # Mantemos o valor atual de 'Status Mensalidade' (campo removido do editor)
                        st.session_state.df.loc[idx] = [
                            cliente['Data'], novo_nome, novo_telefone, novo_veiculo, novo_modelo, nova_placa,
                            novo_plano, novo_valor_adesao, novo_valor_mensalidade,
                            novo_status_adesao, cliente.get('Status Mensalidade', '')
                        ]
                        save_vendas(st.session_state.df)
                        st.success(f"Cliente {novo_nome} atualizado com sucesso!")
                        st.rerun()
