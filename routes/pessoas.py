from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
import mysql.connector

# Importa as ferramentas da raiz do projeto
from database import get_db_connection
from forms import PessoaForm

# CRIA O BLUEPRINT: É como se fosse um "mini-app" dedicado só para Pessoas
pessoas_bp = Blueprint('pessoas', __name__)

@pessoas_bp.route('/pessoas')
@login_required
def index(): # O nome da função não precisa ser mais 'pessoas', pois já estamos no arquivo pessoas.py
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pessoas ORDER BY nome")
    lista_pessoas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('pessoas.html', pessoas=lista_pessoas)

@pessoas_bp.route('/pessoa/novo', methods=['GET', 'POST'])
@login_required
def nova_pessoa():
    form = PessoaForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO pessoas (tipo_pessoa, nome, natureza, cpf_cnpj, endereco, rg, ocupacao, genero, nome_mae) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        val = (
            form.tipo_pessoa.data, form.nome.data, form.natureza.data,
            form.cpf_cnpj.data, form.endereco.data, form.rg.data,
            form.ocupacao.data, form.genero.data, form.nome_mae.data
        )
        try:
            cursor.execute(sql, val)
            conn.commit()
            flash('Pessoa cadastrada com sucesso!', 'success')
            return redirect(url_for('pessoas.index')) # NOTA: Atualizado para apontar pro blueprint
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Erro: Já existe uma pessoa com este CPF/CNPJ.', 'danger')
            else:
                flash(f'Erro ao cadastrar pessoa: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('pessoa_form.html', form=form, title="Nova Pessoa")

@pessoas_bp.route('/pessoa/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pessoa(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pessoas WHERE id = %s", (id,))
    pessoa = cursor.fetchone()
    cursor.close()
    conn.close()
    if not pessoa:
        abort(404)

    form = PessoaForm(data=pessoa)
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """UPDATE pessoas SET tipo_pessoa=%s, nome=%s, natureza=%s, cpf_cnpj=%s, 
                 endereco=%s, rg=%s, ocupacao=%s, genero=%s, nome_mae=%s WHERE id=%s"""
        val = (
            form.tipo_pessoa.data, form.nome.data, form.natureza.data,
            form.cpf_cnpj.data, form.endereco.data, form.rg.data,
            form.ocupacao.data, form.genero.data, form.nome_mae.data, id
        )
        try:
            cursor.execute(sql, val)
            conn.commit()
            flash('Pessoa atualizada com sucesso!', 'success')
            return redirect(url_for('pessoas.index')) # NOTA: Atualizado para apontar pro blueprint
        except mysql.connector.Error as err:
            if err.errno == 1062:
                flash('Erro: Já existe uma pessoa com este CPF/CNPJ.', 'danger')
            else:
                flash(f'Erro ao atualizar pessoa: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('pessoa_form.html', form=form, title="Editar Pessoa")

@pessoas_bp.route('/pessoa/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_pessoa(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM pessoas WHERE id = %s", (id,))
        conn.commit()
        flash('Pessoa excluída com sucesso!', 'success')
    except mysql.connector.Error as err:
        flash(f'Erro: esta pessoa pode estar associada a um processo. Detalhes: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('pessoas.index')) # NOTA: Atualizado para apontar pro blueprint