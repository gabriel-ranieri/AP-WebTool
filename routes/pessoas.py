from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required
import mysql.connector

# Importa as ferramentas da raiz do projeto
from database import get_db_connection
from forms import PessoaForm

pessoas_bp = Blueprint('pessoas', __name__)

def formatar_cpf_cnpj(doc, natureza):
    """Garante a máscara correta baseada na natureza da pessoa antes de salvar no banco."""
    if not doc: return ""
    doc_limpo = "".join(filter(str.isdigit, str(doc)))
    
    if natureza == 'Pessoa Física':
        doc_limpo = doc_limpo.zfill(11)[:11]
        return f"{doc_limpo[:3]}.{doc_limpo[3:6]}.{doc_limpo[6:9]}-{doc_limpo[9:]}"
    elif natureza == 'Empresa':
        doc_limpo = doc_limpo.zfill(14)[:14]
        return f"{doc_limpo[:2]}.{doc_limpo[2:5]}.{doc_limpo[5:8]}/{doc_limpo[8:12]}-{doc_limpo[12:]}"
    return doc

@pessoas_bp.route('/pessoas')
@login_required
def index(): 
    # Captura os filtros da URL (via método GET)
    nome = request.args.get('nome', '')
    tipo_pessoa = request.args.get('tipo_pessoa', '')
    cpf_cnpj = request.args.get('cpf_cnpj', '')

    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Construção da Query Dinâmica
        query = "SELECT * FROM pessoas WHERE 1=1"
        params = []

        if nome:
            query += " AND nome LIKE %s"
            params.append(f"%{nome}%")
        
        if tipo_pessoa:
            query += " AND tipo_pessoa = %s"
            params.append(tipo_pessoa)
            
        if cpf_cnpj:
            query += " AND cpf_cnpj LIKE %s"
            params.append(f"%{cpf_cnpj}%")

        query += " ORDER BY nome"
        
        cursor.execute(query, tuple(params))
        lista_pessoas = cursor.fetchall()
        
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()
    
    # Retornamos os filtros para que os campos continuem preenchidos na tela após buscar
    return render_template('pessoas.html', 
                           pessoas=lista_pessoas, 
                           filtros={
                               'nome': nome,
                               'tipo_pessoa': tipo_pessoa,
                               'cpf_cnpj': cpf_cnpj
                           })

@pessoas_bp.route('/pessoa/novo', methods=['GET', 'POST'])
@login_required
def nova_pessoa():
    form = PessoaForm()
    if form.validate_on_submit():
        cpf_cnpj_perfeito = formatar_cpf_cnpj(form.cpf_cnpj.data, form.natureza.data)
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            sql = """INSERT INTO pessoas (tipo_pessoa, nome, natureza, cpf_cnpj, endereco, rg, ocupacao, genero, nome_mae, nacionalidade, estado_civil, data_nascimento, email) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            val = (
                form.tipo_pessoa.data, form.nome.data, form.natureza.data,
                cpf_cnpj_perfeito, form.endereco.data, form.rg.data,
                form.ocupacao.data, form.genero.data, form.nome_mae.data,
                form.nacionalidade.data, form.estado_civil.data, form.data_nascimento.data, form.email.data
            )
            cursor.execute(sql, val)
            conn.commit()
            flash('Pessoa cadastrada com sucesso!', 'success')
            return redirect(url_for('pessoas.index'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Erro: Já existe uma pessoa com este CPF/CNPJ.', 'danger')
            else:
                flash(f'Erro ao cadastrar pessoa: {err}', 'danger')
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if 'conn' in locals() and conn.is_connected(): conn.close()
            
    return render_template('pessoa_form.html', form=form, title="Nova Pessoa")

@pessoas_bp.route('/pessoa/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pessoa(id):
    # Parte 1: Busca inicial (Blindada)
    conn_fetch = get_db_connection()
    try:
        cursor_fetch = conn_fetch.cursor(dictionary=True)
        cursor_fetch.execute("SELECT * FROM pessoas WHERE id = %s", (id,))
        pessoa = cursor_fetch.fetchone()
    finally:
        if 'cursor_fetch' in locals() and cursor_fetch: cursor_fetch.close()
        if 'conn_fetch' in locals() and conn_fetch.is_connected(): conn_fetch.close()
        
    if not pessoa:
        abort(404)

    form = PessoaForm(data=pessoa)
    
    # Parte 2: Atualização (Blindada)
    if form.validate_on_submit():
        cpf_cnpj_perfeito = formatar_cpf_cnpj(form.cpf_cnpj.data, form.natureza.data)
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            sql = """UPDATE pessoas SET tipo_pessoa=%s, nome=%s, natureza=%s, cpf_cnpj=%s, 
                     endereco=%s, rg=%s, ocupacao=%s, genero=%s, nome_mae=%s,
                     nacionalidade=%s, estado_civil=%s, data_nascimento=%s, email=%s WHERE id=%s"""
            val = (
                form.tipo_pessoa.data, form.nome.data, form.natureza.data,
                cpf_cnpj_perfeito, form.endereco.data, form.rg.data,
                form.ocupacao.data, form.genero.data, form.nome_mae.data,
                form.nacionalidade.data, form.estado_civil.data, form.data_nascimento.data, form.email.data, id
            )
            cursor.execute(sql, val)
            conn.commit()
            flash('Pessoa atualizada com sucesso!', 'success')
            return redirect(url_for('pessoas.index'))
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Erro: Já existe uma pessoa com este CPF/CNPJ.', 'danger')
            else:
                flash(f'Erro ao atualizar pessoa: {err}', 'danger')
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if 'conn' in locals() and conn.is_connected(): conn.close()
            
    return render_template('pessoa_form.html', form=form, title="Editar Pessoa")

@pessoas_bp.route('/pessoa/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_pessoa(id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pessoas WHERE id = %s", (id,))
        conn.commit()
        flash('Pessoa excluída com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro: esta pessoa pode estar associada a um processo. Detalhes: {err}', 'danger')
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()
        
    return redirect(url_for('pessoas.index'))