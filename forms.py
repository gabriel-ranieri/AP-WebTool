from flask_wtf import FlaskForm
from wtforms import (BooleanField, PasswordField, SelectField, StringField,
                     SubmitField, TextAreaField, RadioField, DateField, 
                     TimeField, SelectMultipleField)
from wtforms.validators import DataRequired, Email, InputRequired, Optional
from wtforms.widgets import ListWidget, CheckboxInput

# VALIDADORES DE NÚMERO DE PROCESSO
VALIDADOR_CNJ = r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$'
VALIDADOR_EXECUCAO_FISCAL = r'^\d{15,25}$' 
VALIDADOR_TRABALHISTA = r'^\d{5}-\d{4}\.\d{5}\.\d{2}\.\d{3}$' 

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class PessoaForm(FlaskForm):
    tipo_pessoa = RadioField('Tipo', choices=[('Associado ACRESP', 'Associado ACRESP'), ('Cliente', 'Cliente')], validators=[DataRequired()])
    nome = StringField('Nome / Razão Social', validators=[DataRequired()])
    natureza = RadioField('Natureza', choices=[('Pessoa Física', 'Pessoa Física'), ('Empresa', 'Empresa')], validators=[DataRequired()])
    cpf_cnpj = StringField('CPF / CNPJ', validators=[DataRequired()])
    endereco = TextAreaField('Endereço Completo')
    rg = StringField('RG')
    ocupacao = StringField('Ocupação')
    genero = StringField('Gênero')
    nome_mae = StringField('Nome da Mãe')
    submit = SubmitField('Salvar Pessoa')

class ProcessoForm(FlaskForm):
    pessoa_id = SelectField('Cliente / Executado', coerce=int, validators=[InputRequired(message="Selecione uma pessoa.")])
    categoria_id = SelectField('Categoria do Processo', coerce=int, validators=[DataRequired()])
    status = SelectField('Status do Processo', 
        choices=[
            ('Em Andamento', 'Em Andamento'),
            ('Acordo Celebrado', 'Acordo Celebrado'), 
            ('Acordo Sendo Pago', 'Acordo Sendo Pago'), 
            ('Acordo Quitado', 'Acordo Quitado'), 
            ('Extinto', 'Extinto'), 
            ('Arquivado', 'Arquivado')
        ], 
        validators=[DataRequired()]
    )
    numero = StringField('Número do Processo', validators=[DataRequired()])
    foro = StringField('Foro', validators=[DataRequired()])
    vara = StringField('Vara', validators=[DataRequired()])
    comarca = StringField('Comarca', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class CategoriaForm(FlaskForm):
    nome = StringField('Nome da Categoria', validators=[DataRequired()])
    submit = SubmitField('Salvar Categoria')

class TemplateForm(FlaskForm):
    nome = StringField('Nome do Template', validators=[DataRequired()])
    conteudo = TextAreaField('Conteúdo', validators=[DataRequired()])
    tem_endereco = BooleanField('Incluir Endereço?')
    categoria_id = SelectField('Categoria', coerce=int, validators=[InputRequired()])
    submit = SubmitField('Salvar Template')

class GerarDocumentoForm(FlaskForm):
    processo_id = SelectField('Selecione o Processo', coerce=int, validators=[InputRequired()])
    template_id = SelectField('Selecione o Template de Petição', coerce=int, validators=[InputRequired()])
    submit = SubmitField('Gerar Documento')

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class TarefaForm(FlaskForm):
    titulo = StringField('Título da Tarefa', validators=[DataRequired()])
    descricao = TextAreaField('Descrição / Anotações', validators=[Optional()])
    data_vencimento = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    hora_vencimento = TimeField('Hora (Opcional)', format='%H:%M', validators=[Optional()])
    status = SelectField('Status', choices=[('Pendente', 'Pendente'), ('Em Andamento', 'Em Andamento'), ('Concluída', 'Concluída')], default='Pendente')
    processo_id = SelectField('Vincular a Processo (Opcional)', coerce=int, validators=[Optional()])
    tags = MultiCheckboxField('Tags', coerce=int)
    submit = SubmitField('Salvar Tarefa')

class TagForm(FlaskForm):
    nome = StringField('Nome da Tag', validators=[DataRequired()])
    cor = StringField('Cor', default='#3788d8', validators=[DataRequired()])
    submit = SubmitField('Salvar Tag')