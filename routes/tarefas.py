import os
import uuid
from datetime import date, datetime, timedelta, time
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app, send_from_directory
from flask_login import login_required
import mysql.connector

# Importações do seu projeto
from database import get_db_connection
from forms import TarefaForm, TagForm

tarefas_bp = Blueprint('tarefas', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- HELPERS ---
def get_processos_choices():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, numero FROM processos ORDER BY numero")
        processos = cursor.fetchall()
        return [(0, 'Nenhum')] + [(p[0], p[1]) for p in processos]
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

def get_tags_choices():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM tags ORDER BY nome")
        tags = cursor.fetchall()
        return [(t[0], t[1]) for t in tags]
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

# --- CALENDÁRIO ---
@tarefas_bp.route('/calendario')
@login_required
def calendario():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nome FROM tags ORDER BY nome")
        tags = cursor.fetchall()
        tags_unicas = [t['nome'] for t in tags]
        return render_template('calendario.html', tags_unicas=tags_unicas)
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@tarefas_bp.route('/api/tarefas')
@login_required
def api_tarefas():
    tag_filtro = request.args.get('tag')
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                t.id, t.titulo, t.descricao, t.data_vencimento, t.hora_vencimento, t.status,
                t.processo_id,
                p.numero as processo_numero,
                GROUP_CONCAT(tg.nome SEPARATOR '|') as tags_nomes,
                GROUP_CONCAT(tg.cor SEPARATOR '|') as tags_cores
            FROM tarefas t
            LEFT JOIN processos p ON t.processo_id = p.id
            LEFT JOIN tarefa_tags tt ON t.id = tt.tarefa_id
            LEFT JOIN tags tg ON tt.tag_id = tg.id
        """
        params = []
        
        if tag_filtro and tag_filtro != 'todas':
            query += " WHERE EXISTS (SELECT 1 FROM tarefa_tags tt2 JOIN tags tg2 ON tt2.tag_id = tg2.id WHERE tt2.tarefa_id = t.id AND tg2.nome = %s) "
            params.append(tag_filtro)

        query += " GROUP BY t.id "
        
        if params:
            cursor.execute(query, tuple(params))
        else:
            cursor.execute(query)
            
        tarefas = cursor.fetchall()
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

    eventos = []
    hoje = date.today()
    agora = datetime.now().time()

    for t in tarefas:
        hora_obj = None
        hora_str = ""

        if t['hora_vencimento'] is not None:
            if isinstance(t['hora_vencimento'], timedelta):
                ts = int(t['hora_vencimento'].total_seconds())
                h, r = divmod(ts, 3600)
                m, s = divmod(r, 60)
                hora_obj = time(hour=h, minute=m)
                hora_str = f"{h:02d}:{m:02d}"
            else:
                hora_obj = t['hora_vencimento']
                hora_str = hora_obj.strftime('%H:%M')

        start_date = t['data_vencimento'].strftime('%Y-%m-%d')
        if hora_str:
            start_date += f"T{hora_str}:00"

        atrasada = False
        if t['status'] != 'Concluída':
            if t['data_vencimento'] < hoje:
                atrasada = True
            elif t['data_vencimento'] == hoje and hora_obj and hora_obj < agora:
                atrasada = True

        if t['status'] == 'Concluída':
            cor_evento, cor_texto = '#198754', '#ffffff'
        elif atrasada:
            cor_evento, cor_texto = '#dc3545', '#ffffff'
        elif t['status'] == 'Em Andamento':
            cor_evento, cor_texto = '#0d6efd', '#ffffff'
        else:
            cor_evento, cor_texto = '#ffc107', '#000000'

        titulo_evento = t['titulo']
        if t['processo_numero']:
             titulo_evento = f"[ {t['processo_numero']} ] " + titulo_evento

        tags_list = []
        if t['tags_nomes'] and t['tags_cores']:
            nomes = t['tags_nomes'].split('|')
            cores = t['tags_cores'].split('|')
            tags_list = [{'nome': n, 'cor': c} for n, c in zip(nomes, cores)]

        eventos.append({
            'id': t['id'],
            'title': titulo_evento,
            'start': start_date,
            'color': cor_evento,
            'textColor': cor_texto,
            'extendedProps': {
                'status': t['status'],
                'atrasada': atrasada,
                'descricao': t['descricao'] if t['descricao'] else 'Nenhuma descrição informada.',
                'tags': tags_list,
                'processo_numero': t['processo_numero'],
                'processo_id': t['processo_id'],
                'hora_formatada': hora_str, 
                'data_formatada': t['data_vencimento'].strftime('%d/%m/%Y')
            }
        })

    return jsonify(eventos)

# --- CRUD TAREFAS ---
@tarefas_bp.route('/tarefa/nova', methods=['GET', 'POST'])
@login_required
def nova_tarefa():
    form = TarefaForm()
    form.processo_id.choices = get_processos_choices()
    form.tags.choices = get_tags_choices()

    origem = request.args.get('origem')
    proc_id = request.args.get('processo_id', type=int)

    if request.method == 'GET' and proc_id:
        form.processo_id.data = proc_id

    if form.validate_on_submit():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            processo_id = form.processo_id.data if form.processo_id.data != 0 else None
            sql_tarefa = """INSERT INTO tarefas (titulo, descricao, data_vencimento, hora_vencimento, status, processo_id) 
                            VALUES (%s, %s, %s, %s, %s, %s)"""
            val_tarefa = (form.titulo.data, form.descricao.data, form.data_vencimento.data, 
                          form.hora_vencimento.data, form.status.data, processo_id)
            cursor.execute(sql_tarefa, val_tarefa)
            tarefa_id = cursor.lastrowid

            arquivos = request.files.getlist('anexos')
            for arquivo in arquivos:
                if arquivo and arquivo.filename and allowed_file(arquivo.filename):
                    nome_seguro = secure_filename(arquivo.filename)
                    nome_unico = f"{uuid.uuid4().hex}_{nome_seguro}"
                    caminho_completo = os.path.join(current_app.config['UPLOAD_FOLDER'], nome_unico)
                    arquivo.save(caminho_completo)
                    cursor.execute("""
                        INSERT INTO tarefa_anexos (tarefa_id, nome_original, caminho_arquivo) 
                        VALUES (%s, %s, %s)
                    """, (tarefa_id, nome_seguro, nome_unico))
            
            if form.tags.data:
                sql_tags = "INSERT INTO tarefa_tags (tarefa_id, tag_id) VALUES (%s, %s)"
                for tag_id in form.tags.data:
                    cursor.execute(sql_tags, (tarefa_id, tag_id))

            conn.commit()
            flash('Tarefa adicionada com sucesso ao calendário!', 'success')

            if origem == 'processo' and proc_id:
                return redirect(url_for('processos.ver_processo', id=proc_id))
            return redirect(url_for('tarefas.calendario'))
        except mysql.connector.Error as err:
            flash(f'Erro ao salvar tarefa: {err}', 'danger')
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if 'conn' in locals() and conn.is_connected(): conn.close()

    return render_template('tarefa_form.html', form=form, title="Nova Tarefa", origem=origem, processo_id=proc_id)

@tarefas_bp.route('/tarefa/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_tarefa(id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tarefas WHERE id = %s", (id,))
        tarefa = cursor.fetchone()
        
        if not tarefa:
            abort(404)

        if tarefa.get('hora_vencimento') and isinstance(tarefa['hora_vencimento'], timedelta):
            total_seconds = int(tarefa['hora_vencimento'].total_seconds())
            horas, resto = divmod(total_seconds, 3600)
            minutos, _ = divmod(resto, 60)
            tarefa['hora_vencimento'] = time(hour=horas, minute=minutos)

        cursor.execute("SELECT tag_id FROM tarefa_tags WHERE tarefa_id = %s", (id,))
        tags_atuais = [row['tag_id'] for row in cursor.fetchall()]

        form = TarefaForm(data=tarefa)
        form.processo_id.choices = get_processos_choices()
        form.tags.choices = get_tags_choices()

        origem = request.args.get('origem')
        proc_id_original = tarefa['processo_id']

        cursor.execute("SELECT * FROM tarefa_anexos WHERE tarefa_id = %s", (id,))
        anexos = cursor.fetchall()

        if request.method == 'GET':
            form.tags.data = tags_atuais
            form.processo_id.data = tarefa['processo_id'] if tarefa['processo_id'] else 0

        if form.validate_on_submit():
            try:
                processo_id = form.processo_id.data if form.processo_id.data != 0 else None
                sql_update = """UPDATE tarefas SET titulo=%s, descricao=%s, data_vencimento=%s, 
                                hora_vencimento=%s, status=%s, processo_id=%s WHERE id=%s"""
                val_update = (form.titulo.data, form.descricao.data, form.data_vencimento.data, 
                              form.hora_vencimento.data, form.status.data, processo_id, id)
                cursor.execute(sql_update, val_update)

                cursor.execute("DELETE FROM tarefa_tags WHERE tarefa_id = %s", (id,))
                if form.tags.data:
                    sql_tags = "INSERT INTO tarefa_tags (tarefa_id, tag_id) VALUES (%s, %s)"
                    for tag_id in form.tags.data:
                        cursor.execute(sql_tags, (id, tag_id))
                
                arquivos = request.files.getlist('anexos')
                for arquivo in arquivos:
                    if arquivo and arquivo.filename and allowed_file(arquivo.filename):
                        nome_seguro = secure_filename(arquivo.filename)
                        nome_unico = f"{uuid.uuid4().hex}_{nome_seguro}"
                        caminho_completo = os.path.join(current_app.config['UPLOAD_FOLDER'], nome_unico)
                        arquivo.save(caminho_completo)
                        cursor.execute("""
                            INSERT INTO tarefa_anexos (tarefa_id, nome_original, caminho_arquivo) 
                            VALUES (%s, %s, %s)
                        """, (id, nome_seguro, nome_unico))

                conn.commit()
                flash('Tarefa atualizada com sucesso!', 'success')
                if origem == 'processo' and proc_id_original:
                    return redirect(url_for('processos.ver_processo', id=proc_id_original))
                return redirect(url_for('tarefas.calendario'))
            except mysql.connector.Error as err:
                flash(f'Erro ao atualizar tarefa: {err}', 'danger')

        return render_template('tarefa_form.html', form=form, title="Editar Tarefa", origem=origem, processo_id=proc_id_original, anexos=anexos)
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@tarefas_bp.route('/tarefa/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_tarefa(id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT caminho_arquivo FROM tarefa_anexos WHERE tarefa_id = %s", (id,))
        anexos = cursor.fetchall()

        for anexo in anexos:
            caminho_fisico = os.path.join(current_app.config['UPLOAD_FOLDER'], anexo['caminho_arquivo'])
            try:
                os.remove(caminho_fisico)
            except OSError as e:
                current_app.logger.warning(f"Falha ao deletar {caminho_fisico}: {e}") 

        cursor.execute("DELETE FROM tarefas WHERE id = %s", (id,))
        conn.commit()
        flash('Tarefa excluída com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir tarefa: {err}', 'danger')
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()
        
    return redirect(url_for('tarefas.calendario'))

# --- TAGS ---
@tarefas_bp.route('/tags', methods=['GET', 'POST'])
@login_required
def tags():
    form = TagForm()
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        if form.validate_on_submit():
            try:
                cursor.execute("INSERT INTO tags (nome, cor) VALUES (%s, %s)", (form.nome.data, form.cor.data))
                conn.commit()
                flash('Nova tag criada com sucesso!', 'success')
                return redirect(url_for('tarefas.tags'))
            except mysql.connector.Error as err:
                if err.errno == 1062:
                    flash('Erro: Já existe uma tag com este nome.', 'danger')
                else:
                    flash(f'Erro ao adicionar tag: {err}', 'danger')

        cursor.execute("SELECT * FROM tags ORDER BY nome")
        lista_tags = cursor.fetchall()
        return render_template('tags.html', tags=lista_tags, form=form)
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@tarefas_bp.route('/tag/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_tag(id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id = %s", (id,))
        conn.commit()
        flash('Tag excluída com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro ao excluir tag: {err}', 'danger')
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()
    return redirect(url_for('tarefas.tags'))

# --- ANEXOS ---
@tarefas_bp.route('/anexo/download/<int:id>')
@login_required
def download_anexo(id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tarefa_anexos WHERE id = %s", (id,))
        anexo = cursor.fetchone()
        
        if anexo:
            return send_from_directory(current_app.config['UPLOAD_FOLDER'], anexo['caminho_arquivo'], download_name=anexo['nome_original'], as_attachment=True)
        abort(404)
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@tarefas_bp.route('/anexo/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_anexo(id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tarefa_anexos WHERE id = %s", (id,))
        anexo = cursor.fetchone()
        
        if anexo:
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], anexo['caminho_arquivo']))
            except OSError as e:
                current_app.logger.warning(f"Falha ao apagar anexo físico: {e}") 
                
            cursor.execute("DELETE FROM tarefa_anexos WHERE id = %s", (id,))
            conn.commit()
            flash('Anexo removido.', 'success')
            
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()
        
    return redirect(request.referrer)