import os
import requests
from datetime import date, datetime
from flask import Blueprint, render_template, request, flash
from flask_login import login_required

pje_bp = Blueprint('pje', __name__)

def buscar_comunicacoes_pje(params):
    API_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
    headers = {'accept': 'application/json'}
    params['numeroOab'] = os.getenv('OAB_PADRAO')
    
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status() 
        return response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        flash(f"Erro ao se comunicar com a API do PJE: {e}", "danger")
        return None

@pje_bp.route('/comunicacoes')
@login_required
def comunicacoes_hoje():
    hoje_obj = date.today()
    hoje_api_str = hoje_obj.strftime('%Y-%m-%d')
    hoje_display_str = hoje_obj.strftime('%d/%m/%Y') 

    params = {
        'dataDisponibilizacaoInicio': hoje_api_str,
        'dataDisponibilizacaoFim': hoje_api_str
    }
    
    comunicacoes = buscar_comunicacoes_pje(params)
    
    if comunicacoes:
        for com in comunicacoes:
            try:
                dt_obj = datetime.strptime(com['data_disponibilizacao'], '%Y-%m-%d')
                com['data_formatada'] = dt_obj.strftime('%d/%m/%Y')
            except (ValueError, TypeError):
                com['data_formatada'] = com.get('data_disponibilizacao', 'Data indisponível')
    else:
        comunicacoes = []
        
    return render_template('comunicacoes_hoje.html', comunicacoes=comunicacoes, hoje=hoje_display_str)

@pje_bp.route('/comunicacoes/buscar')
@login_required
def comunicacoes_buscar():
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    numero_processo = request.args.get('numero_processo')
    nome_parte = request.args.get('nome_parte')
    
    resultados = []
    realizou_busca = False
    
    if data_inicio_str and data_fim_str:
        realizou_busca = True
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            
            if data_fim < data_inicio:
                flash("A data final não pode ser anterior à data inicial.", "danger")
            elif (data_fim - data_inicio).days > 30:
                flash("O intervalo de busca não pode exceder 30 dias.", "danger")
            else:
                params = {
                    'dataDisponibilizacaoInicio': data_inicio_str,
                    'dataDisponibilizacaoFim': data_fim_str
                }
                if numero_processo:
                    params['numeroProcesso'] = numero_processo
                if nome_parte:
                    params['nomeParte'] = nome_parte
                
                resultados_api = buscar_comunicacoes_pje(params)
                if resultados_api:
                    for res in resultados_api:
                        try:
                            dt_obj = datetime.strptime(res['data_disponibilizacao'], '%Y-%m-%d')
                            res['data_formatada'] = dt_obj.strftime('%d/%m/%Y')
                        except (ValueError, TypeError):
                            res['data_formatada'] = res.get('data_disponibilizacao', 'Data indisponível')
                    resultados = resultados_api

        except ValueError:
            flash("Formato de data inválido. Use AAAA-MM-DD.", "danger")

    return render_template(
        'comunicacoes_buscar.html', resultados=resultados, realizou_busca=realizou_busca,
        data_inicio=data_inicio_str or '', data_fim=data_fim_str or '',
        numero_processo=numero_processo or '', nome_parte=nome_parte or ''
    )