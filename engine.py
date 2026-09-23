"""Shared real-Python educational sandbox. No imports/attributes/I/O in student code.
AST allowlist + guarded allocation + bounded steps, inside killable worker/process.
"""
import ast, json, math, sys

class FriendlyError(Exception): pass
ALLOWED = set('Module Expr Assign AugAssign AnnAssign Name Load Store Constant List Tuple Dict Set BinOp UnaryOp BoolOp Compare If For While Break Continue Pass FunctionDef arguments arg Return Call keyword Subscript Slice IfExp Add Sub Mult Div FloorDiv Mod UAdd USub Not And Or Eq NotEq Lt LtE Gt GtE In NotIn Is IsNot'.split())
BASE = {'int':int,'float':float,'str':str,'bool':bool,'round':round,'len':len,'abs':abs,'min':min,'max':max,'sum':sum,'enumerate':enumerate,'zip':zip,'range':range}

def bounded(v):
    if isinstance(v,(str,list,tuple,dict,set)) and len(v)>10000: raise FriendlyError('O resultado ficou grande demais. Use os dados curtos do exercício.')
    if isinstance(v,int) and v.bit_length()>256: raise FriendlyError('Número grande demais para este exercício.')
    if isinstance(v,float) and not math.isfinite(v): raise FriendlyError('O cálculo produziu um número fora dos limites.')
    return v

def safe_text(value=''):
    budget=[10000]
    def inspect(v,depth=0):
        budget[0]-=1
        if budget[0]<0 or depth>20: raise FriendlyError('Estrutura grande demais para mostrar. Imprima apenas os valores do exercício.')
        if isinstance(v,(list,tuple,set)):
            for item in v: inspect(item,depth+1)
        elif isinstance(v,dict):
            for key,item in v.items(): inspect(key,depth+1);inspect(item,depth+1)
        elif isinstance(v,str) and len(v)>10000: raise FriendlyError('Texto grande demais.')
    inspect(value)
    text=str(value)
    if len(text)>10000: raise FriendlyError('Texto grande demais para mostrar.')
    return text

def operation(op,a,b):
    if op=='Mult' and isinstance(a,(str,list,tuple)) and isinstance(b,int) and len(a)*b>10000: raise FriendlyError('Repetição grande demais.')
    if op=='Mult' and isinstance(b,(str,list,tuple)) and isinstance(a,int) and len(b)*a>10000: raise FriendlyError('Repetição grande demais.')
    if op=='Mod' and isinstance(a,str): raise FriendlyError('Use print() com vírgulas para formatar a saída.')
    return bounded({'Add':lambda:a+b,'Sub':lambda:a-b,'Mult':lambda:a*b,'Div':lambda:a/b,'FloorDiv':lambda:a//b,'Mod':lambda:a%b}[op]())

class Guard(ast.NodeTransformer):
    def visit_BinOp(self,n):
        self.generic_visit(n)
        return ast.copy_location(ast.Call(func=ast.Name(id='_op',ctx=ast.Load()),args=[ast.Constant(type(n.op).__name__),n.left,n.right],keywords=[]),n)
    def visit_AugAssign(self,n):
        if not isinstance(n.target,ast.Name): raise FriendlyError('Atualize uma variável simples, como total += valor.')
        return self.visit(ast.copy_location(ast.Assign(targets=[n.target],value=ast.BinOp(left=ast.Name(id=n.target.id,ctx=ast.Load()),op=n.op,right=n.value)),n))

def prepare(source,variables=None):
    if len(source)>8000: raise FriendlyError('Use um programa de até 8.000 caracteres.')
    if '___' in source: raise FriendlyError('Preencha a lacuna destacada antes de executar.')
    tree=ast.parse(source)
    nodes=list(ast.walk(tree))
    if len(nodes)>800: raise FriendlyError('Programa grande demais para este terminal.')
    functions={n.name for n in nodes if isinstance(n,ast.FunctionDef)}
    for n in nodes:
        if type(n).__name__ not in ALLOWED: raise FriendlyError('Este terminal aceita o Python dos exercícios: variáveis, cálculos, decisões, laços e funções. Imports e acesso ao sistema não são permitidos.')
        if isinstance(n,(ast.Name,ast.arg,ast.FunctionDef)):
            name=n.id if isinstance(n,ast.Name) else n.arg if isinstance(n,ast.arg) else n.name
            if name.startswith('_'): raise FriendlyError('Use nomes de variáveis sem sublinhado inicial.')
            if name in {*BASE,'input','print'} and (not isinstance(n,ast.Name) or isinstance(n.ctx,ast.Store)): raise FriendlyError('Não substitua as funções padrão do Python.')
        if isinstance(n,ast.Constant): bounded(n.value)
        if isinstance(n,ast.Call) and (not isinstance(n.func,ast.Name) or n.func.id not in {*BASE,'print','input',*functions}): raise FriendlyError('Chame uma função definida no seu código ou uma função básica de Python.')
        if isinstance(n,ast.While):
            controls={x.id for x in ast.walk(n.test) if isinstance(x,ast.Name)}
            writes={x.id for statement in n.body for x in ast.walk(statement) if isinstance(x,ast.Name) and isinstance(x.ctx,ast.Store)}
            exits=any(isinstance(x,(ast.Break,ast.Return)) for statement in n.body for x in ast.walk(statement))
            if not controls.intersection(writes) and not exits: raise FriendlyError('A variável estoque precisa diminuir a cada repetição. O laço foi interrompido com segurança.')
    # Vary the supplied sample inputs; never replace loop updates or function bodies.
    replaced=set()
    for statement in tree.body:
        if isinstance(statement,ast.Assign) and len(statement.targets)==1 and isinstance(statement.targets[0],ast.Name):
            name=statement.targets[0].id
            if variables and name in variables and name not in replaced:
                statement.value=ast.copy_location(ast.Constant(variables[name]),statement.value)
                replaced.add(name)
    return compile(ast.fix_missing_locations(Guard().visit(tree)),'<estudante>','exec'), tree

def evaluate(challenge,source):
    try: prepare(source)
    except Exception as e: return {'passed':False,'tests':[],'output':'','message':friendly(e)}
    cases=cases_for(challenge); results=[]; first_output=''; total_steps=0
    for label,variables,inputs,check in cases:
        code,tree=prepare(source,variables)
        output=[]; iterator=iter(inputs); steps=0
        def emit(*args,sep=' ',end='\n'):
            if len(output)>100: raise FriendlyError('A variável estoque precisa diminuir a cada repetição. O laço foi interrompido com segurança.')
            text=sep.join(safe_text(v) for v in args)+end
            if len(text)>5000: raise FriendlyError('Saída grande demais.')
            output.append(text)
        def read(prompt=''): return next(iterator)
        safe={**BASE,'str':safe_text,'print':emit,'input':read}
        def trace(frame,event,arg):
            nonlocal steps
            if frame.f_code.co_filename=='<estudante>':
                steps+=1
                if steps>12000: raise FriendlyError('A variável estoque precisa diminuir a cada repetição. Execução interrompida com segurança.')
            return trace
        env={'__builtins__':safe,'_op':operation,**variables}
        try:
            sys.settrace(trace)
            exec(code,env,env)
            checked=check(env,''.join(output),tree)
            ok=checked is True
            msg='Aprovado' if ok else checked if isinstance(checked,str) else FEEDBACK.get(challenge,'Seu código funcionou neste exemplo, mas falhou em outro teste.')
        except Exception as e: ok=False; msg=friendly(e)
        finally: sys.settrace(None)
        if not results: first_output=''.join(output)
        results.append({'label':label,'passed':ok,'message':msg}); total_steps+=steps
    return {'passed':all(t['passed'] for t in results),'tests':results,'output':first_output,'message':'Todos os testes aprovados.' if all(t['passed'] for t in results) else next(t['message'] for t in results if not t['passed']),'steps':total_steps}

def friendly(e):
    if isinstance(e,FriendlyError): return str(e)
    if isinstance(e,SyntaxError): return f'Linha {e.lineno}: confira os dois-pontos, os parênteses e a indentação.'
    if isinstance(e,NameError): return 'Uma variável ou parâmetro ainda não foi definido. Confira os nomes e a ordem das instruções.'
    if isinstance(e,TypeError): return 'Confira os tipos e o return: talvez você esteja calculando com texto, com uma função ou com um resultado que não foi devolvido.'
    if isinstance(e,ValueError): return 'O valor informado precisa ser convertido corretamente. Use int() para inteiro e float() para decimal.'
    if isinstance(e,ZeroDivisionError): return 'Não é possível dividir por zero. Confira a operação usada.'
    if isinstance(e,RecursionError): return 'Chamadas repetidas demais. Confira se a função está chamando a si mesma.'
    return 'A execução não pôde terminar. Confira os dados e a condição de parada.'

def eq(a,b): return isinstance(a,(float,int)) and not isinstance(a,bool) and abs(a-b)<0.00001
def has(tree,node): return any(isinstance(n,node) for n in ast.walk(tree))
def calls(tree,name): return any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id==name for n in ast.walk(tree))
def cases_for(c):
    cases=[]
    if c=='tutorial':
        cases.append(('Mensagem na saída',{},[],lambda e,o,t:e.get('mensagem')=='Sistema iniciado' and o.strip()=='Sistema iniciado'))
    elif c=='cadastro':
        cases.extend([
            ('Nome como texto',{},[],lambda e,o,t:e.get('medicamento')=='Paracetamol' and 'Paracetamol' in o),
            ('Quantidade inteira',{},[],lambda e,o,t:True if type(e.get('quantidade')) is int and e['quantidade']==20 else 'A quantidade deve ser um número inteiro: use o valor do cartão sem aspas.'),
            ('Preço decimal',{},[],lambda e,o,t:True if type(e.get('preco')) is float and eq(e['preco'],8.5) else 'O preço deve ser decimal. Use ponto entre a parte inteira e a decimal.'),
            ('Três informações impressas',{},[],lambda e,o,t:'20' in o and '8.5' in o and 'Paracetamol' in o),
        ])
    elif c=='pedido':
        for n,d in [(2,7),(3,5),(1,10)]:
            cases.append((f'{n} por dia × {d} dias',dict(por_dia=n,dias=d),[],lambda e,o,t,n=n,d=d:eq(e.get('total'),n*d) and str(n*d) in o))
    elif c=='geladeira':
        for temp in [9,1.9,2,8,8.1]:
            expected='Muito fria' if temp<2 else 'Adequada' if temp<=8 else 'Muito quente'
            cases.append((f'{temp} °C',dict(temperatura=temp),[],lambda e,o,t,ex=expected:e.get('resultado')==ex and ex in o))
    elif c=='reposicao':
        for n in [7,9,10,15]:
            cases.append((f'{n} caixas',dict(estoque=n),[],lambda e,o,t,n=n:e.get('resultado')==('Repor estoque' if n<10 else 'Estoque adequado')))
    elif c=='esteira':
        for d in [7,1,3,0]:
            cases.append((f'Calendário de {d} dias',dict(dias=d),[],lambda e,o,t,d=d:o.strip().splitlines()==[f'Dia {i}' for i in range(1,d+1)] and has(t,ast.For) and calls(t,'range')))
    elif c=='estoque':
        for n in [5,1,0,3]:
            cases.append((f'Estoque inicial {n}',dict(estoque=n),[],lambda e,o,t,n=n:eq(e.get('estoque'),0) and o.strip().splitlines()==[f'Restam {i}' for i in range(n,0,-1)] and has(t,ast.While)))
    elif c=='micro':
        for n in [500,1000,250]:
            cases.append((f'Converter {n} mg',dict(miligramas=n),[],lambda e,o,t,n=n:eq(e.get('gramas'),n/1000)))
    elif c=='conversor':
        for n in [500,0,1000,250,1250]:
            def check(e,o,t,n=n):
                f=e.get('mg_para_g')
                if not callable(f): return 'Crie a função mg_para_g com o parâmetro mg.'
                if f(n) is None: return 'A função calculou o resultado, mas ainda não o devolveu. Observe return.'
                return eq(f(n),n/1000) and eq(e.get('resultado'),.5) and calls(t,'mg_para_g') and '0.5' in o
            cases.append((f'Função com {n} mg',{},[],check))
    elif c=='iris':
        for price,n in [(8.5,4),(2,9),(3,10),(1.25,0)]:
            def check(e,o,t,p=price,n=n):
                f,g=e.get('calcular_total'),e.get('verificar_estoque')
                if not callable(f) or not callable(g): return 'Mantenha as duas funções e suas chamadas.'
                if f(p,n) is None: return 'A função calculou o resultado, mas ainda não o devolveu. Observe return.'
                return eq(f(p,n),p*n) and g(n)==('Repor estoque' if n<10 else 'Estoque adequado') and eq(e.get('total'),34) and e.get('situacao')=='Repor estoque' and calls(t,'calcular_total') and calls(t,'verificar_estoque') and '34' in o and 'Repor estoque' in o
            cases.append((f'Preço {price} · quantidade {n}',{},[],check))
    else: raise FriendlyError('Desafio desconhecido.')
    return cases

FEEDBACK={
    'cadastro':'Confira os cartões: nome como texto, quantidade inteira 20 e preço decimal 8.50.',
    'pedido':'Use a multiplicação entre por_dia e dias. Seu código deve funcionar também com outros números.',
    'geladeira':'O limite superior da faixa adequada é 8. Teste os valores exatamente iguais a 2 e 8.',
    'reposicao':'Com 9 caixas é preciso repor. Com 10, o estoque já é adequado.',
    'esteira':'O valor final de range() não é incluído. Observe o último dia do calendário.',
    'estoque':'O estoque precisa diminuir dentro do while. Mostre o valor antes de reduzir.',
    'conversor':'A função deve devolver mg / 1000 e ser chamada para calcular resultado.',
    'iris':'Devolva o total calculado e chame verificar_estoque com a quantidade do cartão.',
    'micro':'Divida miligramas por 1000 para converter em gramas.',
    'tutorial':'Preencha a mensagem com Sistema iniciado, mantendo as aspas.',
}

if __name__=='__main__':
    data=json.loads(sys.stdin.read(20000))
    print(json.dumps(evaluate(data['challenge'],data['code']),ensure_ascii=True))
