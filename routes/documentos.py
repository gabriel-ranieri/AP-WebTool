import os
import uuid
from datetime import datetime
import locale
from docxtpl import DocxTemplate
from jinja2 import Template
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory, current_app
from flask_login import login_required
import mysql.connector

from database import get_db_connection
from forms import TemplateForm, GerarDocumentoForm

documentos_bp = Blueprint('documentos', __name__)

# --- HELPERS ---
def obter_data_extenso(data=None):
    if data is None:
        data = datetime.today().date()
    meses = {1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril', 5: 'maio', 6: 'junho',
             7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'}
    return f"{data.day} de {meses[data.month]} de {data.year}"

def limpar_arquivos_antigos():
    pasta_temp = os.path.join(current_app.root_path, 'temp_docs')
    os.makedirs(pasta_temp, exist_ok=True)
    tempo_limite = 7200 
    tempo_atual = datetime.now().timestamp()

    for arquivo in os.listdir(pasta_temp):
        caminho_arquivo = os.path.join(pasta_temp, arquivo)
        if os.path.isfile(caminho_arquivo):
            tempo_criacao = os.path.getmtime(caminho_arquivo)
            if (tempo_atual - tempo_criacao) > tempo_limite:
                try:
                    os.remove(caminho_arquivo)
                except OSError as e:
                    current_app.logger.warning(f"Coletor de Lixo falhou ao deletar {caminho_arquivo}: {e}")

def get_categorias_choices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    return [(c[0], c[1]) for c in categorias]

# --- TEMPLATES CRUD ---
@documentos_bp.route('/templates')
@login_required
def templates():
    search_nome = request.args.get('nome', '')
    filter_categoria = request.args.get('categoria', '', type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM categorias ORDER BY nome")
    categorias_list = cursor.fetchall()

    query_base = """
    SELECT t.*, c.nome as categoria_nome 
    FROM templates t 
    JOIN categorias c ON t.categoria_id = c.id
    WHERE 1=1
    """
    params = []
    
    if search_nome:
        query_base += " AND t.nome LIKE %s"
        params.append(f"%{search_nome}%")
    if filter_categoria:
        query_base += " AND t.categoria_id = %s"
        params.append(filter_categoria)
        
    query_base += " ORDER BY t.nome"
    
    cursor.execute(query_base, tuple(params))
    lista_templates = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('templates.html', templates=lista_templates, categorias=categorias_list,
                           current_nome=search_nome, current_categoria=filter_categoria)

@documentos_bp.route('/template/novo', methods=['GET', 'POST'])
@login_required
def novo_template():
    form = TemplateForm()
    form.categoria_id.choices = get_categorias_choices()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            sql = "INSERT INTO templates (nome, conteudo, tem_endereco, categoria_id) VALUES (%s, %s, %s, %s)"
            val = (form.nome.data, form.conteudo.data, form.tem_endereco.data, form.categoria_id.data)
            cursor.execute(sql, val)
            conn.commit()
            flash('Template criado com sucesso!', 'success')
            return redirect(url_for('documentos.templates'))
        except mysql.connector.Error as err:
            flash(f'Erro ao criar template: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('template_form.html', form=form, title="Novo Template")

@documentos_bp.route('/template/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_template(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM templates WHERE id = %s", (id,))
    template_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not template_data:
        abort(404)

    form = TemplateForm(data=template_data)
    form.categoria_id.choices = get_categorias_choices()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE templates SET nome=%s, conteudo=%s, tem_endereco=%s, categoria_id=%s WHERE id=%s"
        val = (form.nome.data, form.conteudo.data, form.tem_endereco.data, form.categoria_id.data, id)
        cursor.execute(sql, val)
        conn.commit()
        flash('Template atualizado com sucesso!', 'success')
        return redirect(url_for('documentos.templates'))
    return render_template('template_form.html', form=form, title="Editar Template")

@documentos_bp.route('/template/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_template(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM templates WHERE id = %s", (id,))
    conn.commit()
    flash('Template excluído com sucesso!', 'success')
    return redirect(url_for('documentos.templates'))

# --- GERAÇÃO DE DOCUMENTOS ---
@documentos_bp.route('/gerar_documento', methods=['GET', 'POST'])
@login_required
def gerar_documento():
    limpar_arquivos_antigos()
    form = GerarDocumentoForm()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT p.id, CONCAT(p.numero, ' - ', pe.nome) as display FROM processos p JOIN pessoas pe ON p.pessoa_id = pe.id ORDER BY pe.nome")
    form.processo_id.choices = [(p[0], p[1]) for p in cursor.fetchall()]
    
    cursor.execute("SELECT t.id, CONCAT(c.nome, ' - ', t.nome) as display FROM templates t JOIN categorias c ON t.categoria_id = c.id ORDER BY c.nome, t.nome")
    form.template_id.choices = [(t[0], t[1]) for t in cursor.fetchall()]
    
    if form.validate_on_submit():
        processo_id = form.processo_id.data
        template_id = form.template_id.data
        
        cursor_dict = conn.cursor(dictionary=True)
        cursor_dict.execute("""
            SELECT pr.*, pe.nome as executado_nome, pe.cpf_cnpj as executado_cpf, 
                   pe.endereco as executado_endereco, pe.rg as executado_rg, 
                   pe.ocupacao as executado_ocupacao, pe.genero as executado_genero,
                   pe.nome_mae as executado_nome_mae
            FROM processos pr 
            JOIN pessoas pe ON pr.pessoa_id = pe.id 
            WHERE pr.id = %s
        """, (processo_id,))
        processo = cursor_dict.fetchone()
        
        cursor_dict.execute("SELECT * FROM templates WHERE id = %s", (template_id,))
        template_obj = cursor_dict.fetchone()

        if not processo or not template_obj:
            flash('Processo ou Template não encontrado.', 'danger')
            return redirect(url_for('documentos.gerar_documento'))
            
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')

        hoje = datetime.now()
        data_por_extenso = hoje.strftime('%d de %B de %Y')
        
        render_context = {
            'processo_vara': processo['vara'],
            'processo_foro': processo['foro'],
            'processo_comarca': processo['comarca'],
            'processo_numero': processo['numero'],
            'executado_nome': processo['executado_nome'],
            'data_por_extenso': data_por_extenso,
            'data_hoje': obter_data_extenso()
        }
        
        template_string_db = template_obj['conteudo']
        jinja_template = Template(template_string_db)
        corpo_peticao_renderizado = jinja_template.render(render_context)

        try:
            modelo_dir = os.path.join(current_app.root_path, 'modelos')
            temp_dir = os.path.join(current_app.root_path, 'temp_docs')
            
            doc = DocxTemplate(os.path.join(modelo_dir, 'modelo_peticao.docx'))
            docxtpl_context = {'corpo_peticao': corpo_peticao_renderizado}
            docxtpl_context.update(render_context)
            doc.render(docxtpl_context)
            
            filename_base = f"peticao_{processo['numero'].replace('.', '_')}_{uuid.uuid4().hex[:8]}"
            output_docx_path = os.path.join(temp_dir, f"{filename_base}.docx")
            doc.save(output_docx_path)

            cursor_tracker = conn.cursor()
            sql_tracker = "INSERT INTO peticoes_geradas (processo_id, template_id, data_geracao) VALUES (%s, %s, %s)"
            val_tracker = (processo_id, template_id, datetime.now())
            cursor_tracker.execute(sql_tracker, val_tracker)
            conn.commit()
            cursor_tracker.close()
            
            return redirect(url_for('documentos.confirmacao_geracao', filename_base=filename_base))

        except Exception as e:
            flash(f'Ocorreu um erro ao gerar o documento: {e}', 'danger')

    cursor.close()
    conn.close()
    return render_template('gerar_documento_form.html', form=form)

@documentos_bp.route('/confirmacao_geracao/<filename_base>')
@login_required
def confirmacao_geracao(filename_base):
    temp_dir = os.path.join(current_app.root_path, 'temp_docs')
    docx_path = os.path.join(temp_dir, f"{filename_base}.docx")
    
    if not os.path.exists(docx_path):
        abort(404)
        
    return render_template('confirmacao_geracao.html', filename_base=filename_base)

@documentos_bp.route('/download/<filetype>/<filename_base>')
@login_required
def download_file(filetype, filename_base):
    if filetype == 'docx':
        filename = f"{filename_base}.docx"
        temp_dir = os.path.join(current_app.root_path, 'temp_docs')
        if os.path.exists(os.path.join(temp_dir, filename)):
            return send_from_directory(temp_dir, filename, as_attachment=True)
        else:
            abort(404)
    abort(400)