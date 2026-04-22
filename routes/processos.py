import os
import re
from math import ceil
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required
import mysql.connector

# Importações do seu projeto
from database import get_db_connection
from forms import ProcessoForm, CategoriaForm, VALIDADOR_CNJ, VALIDADOR_EXECUCAO_FISCAL, VALIDADOR_TRABALHISTA

processos_bp = Blueprint('processos', __name__)

# --- FUNÇÕES AUXILIARES ---
def get_pessoas_choices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, CONCAT(nome, ' - ', cpf_cnpj) as display FROM pessoas ORDER BY nome")
    pessoas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [(p[0], p[1]) for p in pessoas]

def get_categorias_choices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    return [(c[0], c[1]) for c in categorias]

# --- ROTAS DE PROCESSOS ---

@processos_bp.route('/processos')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '')
    filter_foro = request.args.get('foro', '')
    filter_comarca = request.args.get('comarca', '')
    filter_status = request.args.get('status', '')
    
    per_page = 15
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    from_join_clause = """
        FROM processos p
        JOIN pessoas pe ON p.pessoa_id = pe.id
        JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN peticoes_geradas pg ON p.id = pg.processo_id
    """
    where_clause = " WHERE 1=1 "
    params = []
    
    if search_term:
        where_clause += " AND p.numero LIKE %s "
        params.append(f"%{search_term}%")
    if filter_foro:
        where_clause += " AND p.foro = %s "
        params.append(filter_foro)
    if filter_comarca:
        where_clause += " AND p.comarca = %s "
        params.append(filter_comarca)
    if filter_status:
        where_clause += " AND p.status = %s "
        params.append(filter_status)
        
    count_query = f"SELECT COUNT(DISTINCT p.id) as total {from_join_clause} {where_clause}"
    cursor.execute(count_query, tuple(params))
    total_results = cursor.fetchone()['total']
    total_pages = ceil(total_results / per_page) if total_results > 0 else 0
    
    select_clause = """
        SELECT 
            p.id, p.numero, p.foro, p.vara, p.comarca, p.status, 
            pe.nome as executado_nome, 
            c.nome as categoria_nome, 
            COUNT(pg.id) as total_peticoes,
            MAX(pg.data_geracao) as ultima_atividade
    """
    group_by_clause = " GROUP BY p.id, pe.nome, c.nome "
    order_by_clause = " ORDER BY pe.nome ASC "
    limit_clause = " LIMIT %s OFFSET %s "
    
    data_query = select_clause + from_join_clause + where_clause + group_by_clause + order_by_clause + limit_clause
    
    final_params = tuple(params) + (per_page, offset)
    cursor.execute(data_query, final_params)
    processos_list = cursor.fetchall()
    
    tres_meses_atras = datetime.now() - timedelta(days=90)
    for processo in processos_list:
        ua = processo['ultima_atividade']
        processo['alerta_inativo'] = (ua is not None and ua < tres_meses_atras)

    cursor.execute("SELECT DISTINCT foro FROM processos ORDER BY foro")
    foros = [row['foro'] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT comarca FROM processos ORDER BY comarca")
    comarcas = [row['comarca'] for row in cursor.fetchall()]
    status_list = ['Em Andamento','Acordo Celebrado','Acordo Sendo Pago','Acordo Quitado','Extinto','Arquivado']

    cursor.close()
    conn.close()

    return render_template('processos.html', processos=processos_list, page=page, total_pages=total_pages,
                           foros=foros, comarcas=comarcas, status_list=status_list,
                           current_search=search_term, current_foro=filter_foro,
                           current_comarca=filter_comarca, current_status=filter_status)

@processos_bp.route('/processo/novo', methods=['GET', 'POST'])
@login_required
def novo_processo():
    form = ProcessoForm()
    form.pessoa_id.choices = get_pessoas_choices()
    form.categoria_id.choices = get_categorias_choices() 
    
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()

        categoria_id = form.categoria_id.data
        numero_processo = form.numero.data
        
        cursor_dict = conn.cursor(dictionary=True)
        cursor_dict.execute("SELECT nome FROM categorias WHERE id = %s", (categoria_id,))
        categoria_nome = cursor_dict.fetchone()['nome']
        cursor_dict.close()

        valid = True
        if categoria_nome == 'Trabalhista':
            if not re.match(VALIDADOR_TRABALHISTA, numero_processo):
                flash(f'Formato Trabalhista inválido. (Ex: {VALIDADOR_TRABALHISTA})', 'danger')
                valid = False
        else: 
            if not re.match(VALIDADOR_CNJ, numero_processo):
                flash(f'Formato CNJ inválido. (Ex: {VALIDADOR_CNJ})', 'danger')
                valid = False
        
        if not valid:
            return render_template('processo_form.html', form=form, title="Novo Processo")

        try:
            sql = """INSERT INTO processos (numero, foro, vara, comarca, pessoa_id, status, categoria_id) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            val = (form.numero.data, form.foro.data.upper(), form.vara.data.upper(), form.comarca.data.upper(),
                   form.pessoa_id.data, form.status.data, form.categoria_id.data)
            cursor.execute(sql, val)
            conn.commit()
            flash('Processo adicionado com sucesso!', 'success')
            return redirect(url_for('processos.index'))
        except mysql.connector.Error as err:
            flash(f'Erro ao adicionar processo: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('processo_form.html', form=form, title="Novo Processo")

@processos_bp.route('/processo/<int:id>')
@login_required
def ver_processo(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT p.*, pe.nome as cliente_nome, pe.cpf_cnpj as cliente_cpf, pe.ocupacao as cliente_ocupacao,
               c.nome as categoria_nome 
        FROM processos p
        JOIN pessoas pe ON p.pessoa_id = pe.id
        JOIN categorias c ON p.categoria_id = c.id
        WHERE p.id = %s
    """, (id,))
    processo = cursor.fetchone()
    
    if not processo:
        cursor.close()
        conn.close()
        abort(404)
        
    cursor.execute("""
        SELECT t.*, 
               GROUP_CONCAT(tg.nome SEPARATOR '|') as tags_nomes,
               GROUP_CONCAT(tg.cor SEPARATOR '|') as tags_cores
        FROM tarefas t
        LEFT JOIN tarefa_tags tt ON t.id = tt.tarefa_id
        LEFT JOIN tags tg ON tt.tag_id = tg.id
        WHERE t.processo_id = %s
        GROUP BY t.id
        ORDER BY t.data_vencimento ASC
    """, (id,))
    tarefas = cursor.fetchall()
    
    hoje = date.today()
    agora = datetime.now().time()
    tags_processo = set() 
    
    for t in tarefas:
        t['atrasada'] = False
        if t['status'] != 'Concluída':
            if t['data_vencimento'] < hoje:
                t['atrasada'] = True
            elif t['data_vencimento'] == hoje and t['hora_vencimento'] and t['hora_vencimento'] < agora:
                t['atrasada'] = True
                
        t['tags_list'] = []
        if t['tags_nomes'] and t['tags_cores']:
            nomes = t['tags_nomes'].split('|')
            cores = t['tags_cores'].split('|')
            t['tags_list'] = [{'nome': n, 'cor': c} for n, c in zip(nomes, cores)]
            for n in nomes:
                tags_processo.add(n)

    def peso_tarefa(t):
        if t['atrasada']: return 1
        if t['status'] in ['Pendente', 'Em Andamento']: return 2
        if t['status'] == 'Concluída': return 3
        return 4

    tarefas.sort(key=lambda t: (peso_tarefa(t), t['data_vencimento'] or date.max))
    tags_unicas = sorted(list(tags_processo))

    cursor.close()
    conn.close()
    
    return render_template('processo_detalhe.html', processo=processo, tarefas=tarefas, tags_unicas=tags_unicas)

@processos_bp.route('/processo/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_processo(id):
    conn_fetch = get_db_connection()
    cursor_fetch = conn_fetch.cursor(dictionary=True)
    cursor_fetch.execute("SELECT * FROM processos WHERE id = %s", (id,))
    processo = cursor_fetch.fetchone()
    cursor_fetch.close()
    conn_fetch.close()

    if not processo:
        abort(404)

    form = ProcessoForm(data=processo)
    form.pessoa_id.choices = get_pessoas_choices()
    form.categoria_id.choices = get_categorias_choices()
    
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()

        categoria_id = form.categoria_id.data
        numero_processo = form.numero.data
        
        cursor_dict = conn.cursor(dictionary=True)
        cursor_dict.execute("SELECT nome FROM categorias WHERE id = %s", (categoria_id,))
        categoria_nome = cursor_dict.fetchone()['nome']
        cursor_dict.close()

        valid = True
        if categoria_nome == 'Execução Fiscal':
            if not re.match(VALIDADOR_EXECUCAO_FISCAL, numero_processo):
                flash(f'Formato de Execução Fiscal inválido.', 'danger')
                valid = False
        elif categoria_nome == 'Trabalhista':
            if not re.match(VALIDADOR_TRABALHISTA, numero_processo):
                flash(f'Formato Trabalhista inválido.', 'danger')
                valid = False
        else: 
            if not re.match(VALIDADOR_CNJ, numero_processo):
                flash(f'Formato CNJ inválido.', 'danger')
                valid = False

        if not valid:
            return render_template('processo_form.html', form=form, title="Editar Processo")

        try:
            sql = """UPDATE processos SET numero=%s, foro=%s, vara=%s, comarca=%s, 
                     pessoa_id=%s, status=%s, categoria_id=%s WHERE id=%s"""
            val = (form.numero.data, form.foro.data.upper(), form.vara.data.upper(), form.comarca.data.upper(),
                   form.pessoa_id.data, form.status.data, form.categoria_id.data, id)
            cursor.execute(sql, val)
            conn.commit()
            flash('Processo atualizado com sucesso!', 'success')
            
            origem = request.args.get('origem')
            if origem == 'calendario':
                return redirect(url_for('calendario')) # O calendário ainda não está em blueprint!
            return redirect(url_for('processos.ver_processo', id=id))
        except mysql.connector.Error as err:
            flash(f'Erro ao atualizar processo: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('processo_form.html', form=form, title="Editar Processo")

@processos_bp.route('/processo/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_processo(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.caminho_arquivo 
            FROM tarefa_anexos a
            JOIN tarefas t ON a.tarefa_id = t.id
            WHERE t.processo_id = %s
        """, (id,))
        anexos_para_deletar = cursor.fetchall()

        # Usando o current_app porque app não existe aqui!
        for anexo in anexos_para_deletar:
            caminho_fisico = os.path.join(current_app.config['UPLOAD_FOLDER'], anexo['caminho_arquivo'])
            try:
                os.remove(caminho_fisico)
            except OSError as e:
                current_app.logger.warning(f"Falha ao apagar anexo {caminho_fisico}: {e}")
                
        cursor.execute("DELETE FROM processos WHERE id = %s", (id,))
        conn.commit()
        flash('Processo excluído com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir processo: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('processos.index'))

# --- ROTAS DE CATEGORIAS ---

@processos_bp.route('/categorias', methods=['GET', 'POST'])
@login_required
def categorias():
    form = CategoriaForm()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if form.validate_on_submit():
        try:
            cursor.execute("INSERT INTO categorias (nome) VALUES (%s)", (form.nome.data,))
            conn.commit()
            flash('Categoria adicionada com sucesso!', 'success')
            return redirect(url_for('processos.categorias'))
        except mysql.connector.Error as err:
            flash(f'Erro ao adicionar categoria: {err}', 'danger')
    
    cursor.execute("SELECT * FROM categorias ORDER BY nome")
    lista_categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('categorias.html', categorias=lista_categorias, form=form)

@processos_bp.route('/categoria/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_categoria(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM categorias WHERE id = %s", (id,))
        conn.commit()
        flash('Categoria excluída com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro: esta categoria pode estar em uso. Detalhes: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('processos.categorias'))