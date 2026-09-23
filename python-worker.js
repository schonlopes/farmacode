const runtimeBase=new URL('./pyodide/',self.location.href).href;
importScripts(new URL('pyodide.js',runtimeBase).href);
let runtime;
async function initialize(){
  const python=await loadPyodide({indexURL:runtimeBase});
  python.globals.set('__name__','farmacode_worker');
  const response=await fetch(new URL('./engine.py',self.location.href));
  if(!response.ok)throw Error('Avaliador Python indisponível.');
  await python.runPythonAsync(await response.text());
  return python;
}
onmessage=async({data})=>{
  try{
    runtime??=initialize();const python=await runtime;
    if(data.type==='initialize'){postMessage({id:data.id,type:'ready'});return;}
    python.globals.set('student_payload',JSON.stringify({challenge:data.challenge,source:data.source}));
    const result=await python.runPythonAsync('json.dumps(evaluate(**json.loads(student_payload)))');
    postMessage({id:data.id,type:'result',result:JSON.parse(result)});
  }catch(error){console.error('FarmaCode Worker:',error);postMessage({id:data.id,type:'error',message:'Não foi possível preparar o Python. Confira a conexão inicial e tente novamente.'});}
};
