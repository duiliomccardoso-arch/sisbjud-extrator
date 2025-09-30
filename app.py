import streamlit as st
import pdfplumber
import re
from num2words import num2words
import io

# Configuração da página
st.set_page_config(
    page_title="Gerador de Resumos SISBAJUD",
    page_icon="⚖️",
    layout="wide"
)

def formatar_valor_extenso(valor):
    """Converte valor numérico para extenso em português"""
    try:
        valor_float = float(valor.replace('.', '').replace(',', '.'))
        
        # Separar reais e centavos
        reais = int(valor_float)
        centavos = int(round((valor_float - reais) * 100))
        
        # Converter para extenso
        reais_extenso = num2words(reais, lang='pt_BR')
        centavos_extenso = num2words(centavos, lang='pt_BR')
        
        # Formatação
        if reais == 1:
            parte_reais = "um real"
        else:
            parte_reais = f"{reais_extenso} reais"
        
        if centavos == 0:
            return f"{parte_reais}"
        elif centavos == 1:
            return f"{parte_reais} e um centavo"
        else:
            return f"{parte_reais} e {centavos_extenso} centavos"
    except:
        return "valor não identificado"

def extrair_bloqueios(pdf_file):
    """Extrai informações de bloqueios do PDF"""
    bloqueios = []
    
    with pdfplumber.open(pdf_file) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"
    
    # Padrão para identificar réus/executados com CPF/CNPJ e valor total
    padrao_reu = r'(\d{11,14}):\s*([A-ZÀ-Ú\s]+(?:[A-ZÀ-Ú\s]+)?)\s+R\$\s*([\d.,]+)'
    
    matches = re.finditer(padrao_reu, texto_completo)
    
    for match in matches:
        cpf_cnpj = match.group(1)
        nome = match.group(2).strip()
        valor = match.group(3)
        
        # Determinar tipo de documento
        if len(cpf_cnpj) == 11:
            tipo_doc = "CPF"
            doc_formatado = f"{cpf_cnpj[:3]}.{cpf_cnpj[3:6]}.{cpf_cnpj[6:9]}-{cpf_cnpj[9:]}"
        else:
            tipo_doc = "CNPJ"
            doc_formatado = f"{cpf_cnpj[:2]}.{cpf_cnpj[2:5]}.{cpf_cnpj[5:8]}/{cpf_cnpj[8:12]}-{cpf_cnpj[12:]}"
        
        # Verificar se o valor é maior que zero
        valor_float = float(valor.replace('.', '').replace(',', '.'))
        if valor_float > 0:
            bloqueios.append({
                'nome': nome,
                'documento': cpf_cnpj,
                'tipo_doc': tipo_doc,
                'doc_formatado': doc_formatado,
                'valor': valor,
                'valor_float': valor_float
            })
    
    return bloqueios

def gerar_resumos(bloqueios):
    """Gera os resumos formatados"""
    resumos = []
    
    for bloqueio in bloqueios:
        valor_extenso = formatar_valor_extenso(bloqueio['valor'])
        
        resumo = (
            f"R$ {bloqueio['valor']} ({valor_extenso}), bloqueados via Sisbajud, "
            f"de titularidade de {bloqueio['nome']} "
            f"({bloqueio['tipo_doc']} {bloqueio['doc_formatado']})"
        )
        
        resumos.append(resumo)
    
    return resumos

# Interface do Streamlit
st.title("⚖️ Gerador de Resumos de Bloqueios SISBAJUD")
st.markdown("---")

# Informações sobre a ferramenta
with st.expander("ℹ️ Sobre esta ferramenta"):
    st.markdown("""
    Esta ferramenta extrai automaticamente informações de bloqueios bancários de documentos SISBAJUD e gera resumos formatados.
    
    **Como usar:**
    1. Faça upload do arquivo PDF do SISBAJUD
    2. Aguarde o processamento
    3. Visualize os resumos gerados
    4. Copie ou baixe os resultados
    
    **Segurança:**
    - Os arquivos não são armazenados no servidor
    - O processamento é feito em tempo real
    - Dados são descartados após o processamento
    """)

# Aviso de confidencialidade
st.warning("⚠️ **ATENÇÃO:** Este sistema processa dados sensíveis. Certifique-se de estar em ambiente seguro e autorizado.")

# Upload do arquivo
uploaded_file = st.file_uploader(
    "Selecione o arquivo PDF do SISBAJUD",
    type=['pdf'],
    help="Faça upload do documento PDF gerado pelo sistema SISBAJUD"
)

if uploaded_file is not None:
    with st.spinner("Processando arquivo..."):
        try:
            # Extrair bloqueios
            bloqueios = extrair_bloqueios(uploaded_file)
            
            if not bloqueios:
                st.error("❌ Nenhum bloqueio identificado no arquivo. Verifique se o arquivo está no formato correto.")
            else:
                # Mostrar estatísticas
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total de Bloqueios", len(bloqueios))
                
                total_geral = sum(b['valor_float'] for b in bloqueios)
                total_geral_formatado = f"{total_geral:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
                
                with col2:
                    st.metric("Valor Total Bloqueado", f"R$ {total_geral_formatado}")
                
                st.markdown("---")
                
                # Gerar resumos
                resumos = gerar_resumos(bloqueios)
                
                # Exibir resumos
                st.subheader("📋 Resumos dos Bloqueios")
                
                for i, resumo in enumerate(resumos, 1):
                    with st.container():
                        st.markdown(f"**{i}.** {resumo}")
                        st.markdown("")
                
                st.markdown("---")
                
                # Valor total por extenso
                total_geral_extenso = formatar_valor_extenso(total_geral_formatado)
                st.success(f"**VALOR TOTAL BLOQUEADO:** R$ {total_geral_formatado} ({total_geral_extenso})")
                
                # Preparar texto para download
                texto_download = "RESUMOS DOS BLOQUEIOS BANCÁRIOS - SISBAJUD\n"
                texto_download += "=" * 80 + "\n\n"
                
                for i, resumo in enumerate(resumos, 1):
                    texto_download += f"{i}. {resumo}\n\n"
                
                texto_download += "=" * 80 + "\n"
                texto_download += f"VALOR TOTAL BLOQUEADO: R$ {total_geral_formatado} ({total_geral_extenso})\n"
                texto_download += "=" * 80 + "\n"
                
                # Botão de download
                st.download_button(
                    label="📥 Baixar Resumos (TXT)",
                    data=texto_download,
                    file_name="resumos_bloqueios_sisbajud.txt",
                    mime="text/plain"
                )
                
                # Botão para copiar todos os resumos
                st.markdown("---")
                with st.expander("📋 Copiar Todos os Resumos"):
                    st.code(texto_download, language=None)
                
        except Exception as e:
            st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
            st.info("Verifique se o arquivo está no formato correto do SISBAJUD.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px;'>
    Desenvolvido para processamento de documentos SISBAJUD | Versão 1.0
    </div>
    """,
    unsafe_allow_html=True
)
