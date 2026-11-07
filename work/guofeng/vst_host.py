"""Minimal offline VST2 host (32-bit Python). Renders a composition, not a sample bank."""
import ctypes as C,struct,json,sys,wave,array,os
from pathlib import Path
ip=C.c_int32;ptr=C.c_void_p;sp=C.c_ssize_t
class AEffect(C.Structure):pass
CB=C.CFUNCTYPE(sp,C.POINTER(AEffect),ip,ip,sp,ptr,C.c_float)
Dispatch=C.CFUNCTYPE(sp,C.POINTER(AEffect),ip,ip,sp,ptr,C.c_float)
Process=C.CFUNCTYPE(None,C.POINTER(AEffect),C.POINTER(C.POINTER(C.c_float)),C.POINTER(C.POINTER(C.c_float)),ip)
AEffect._fields_=[('magic',ip),('dispatcher',ptr),('process',ptr),('setParameter',ptr),('getParameter',ptr),('numPrograms',ip),('numParams',ip),('numInputs',ip),('numOutputs',ip),('flags',ip),('resvd1',sp),('resvd2',sp),('initialDelay',ip),('realQualities',ip),('offQualities',ip),('ioRatio',C.c_float),('object',ptr),('user',ptr),('uniqueID',ip),('version',ip),('processReplacing',ptr),('processDoubleReplacing',ptr),('future',C.c_char*56)]
class Midi(C.Structure):
 _fields_=[('type',ip),('byteSize',ip),('deltaFrames',ip),('flags',ip),('noteLength',ip),('noteOffset',ip),('midiData',C.c_ubyte*4),('detune',C.c_byte),('noteOffVelocity',C.c_ubyte),('reserved1',C.c_ubyte),('reserved2',C.c_ubyte)]
class Events(C.Structure):
 _fields_=[('numEvents',ip),('reserved',sp),('events',ptr*256)]
class Time(C.Structure):
 _fields_=[('samplePos',C.c_double),('sampleRate',C.c_double),('nanoSeconds',C.c_double),('ppqPos',C.c_double),('tempo',C.c_double),('barStartPos',C.c_double),('cycleStartPos',C.c_double),('cycleEndPos',C.c_double),('timeSigNumerator',ip),('timeSigDenominator',ip),('smpteOffset',ip),('smpteFrameRate',ip),('samplesToNextClock',ip),('flags',ip)]
SR=44100;BLOCK=512;timeinfo=Time();timeinfo.sampleRate=SR;timeinfo.tempo=112;timeinfo.timeSigNumerator=4;timeinfo.timeSigDenominator=4;timeinfo.flags=2|512|1024|2048|8192
@CB
def host(effect,opcode,index,value,p,opt):
 if opcode==1:return 2400
 if opcode==16:return SR
 if opcode==17:return BLOCK
 if opcode==7:return C.addressof(timeinfo)
 if opcode==32:
  if p:C.memmove(p,b'Python Offline\0',15)
  return 1
 if opcode==33:
  if p:C.memmove(p,b'Guofeng Music\0',14)
  return 1
 if opcode==34:return 1000
 if opcode==37:return 1
 if opcode==23:return 2
 return 0
plugin,plan,out=sys.argv[1:4]
plan=json.loads(Path(plan).read_text());duration=plan['duration'];midi=sorted(plan['events'],key=lambda x:x[0]);cursor=0
lib=C.CDLL(str(Path(plugin).resolve()));entry=getattr(lib,'VSTPluginMain',None) or getattr(lib,'main');entry.argtypes=[CB];entry.restype=C.POINTER(AEffect)
e=entry(host);a=e.contents;print('plugin',plugin,'programs',a.numPrograms,'params',a.numParams,'inputs',a.numInputs,'outputs',a.numOutputs,'magic',hex(a.magic),flush=True)
dispatch=Dispatch(a.dispatcher)
def d(op,i=0,v=0,p=None,f=0.):return dispatch(e,op,i,v,p,f)
d(0);d(10,f=SR);d(11,v=BLOCK);d(2,v=0);d(12,v=1);d(71)
names=[]
for i in range(a.numPrograms):
 d(2,v=i);bb=C.create_string_buffer(256);d(5,p=C.cast(bb,ptr));names.append(bb.value.decode('latin1'))
print('PROGRAMS',names,flush=True);d(2,v=plan.get('program',0))
getter=C.CFUNCTYPE(C.c_float,C.POINTER(AEffect),ip)(a.getParameter)
paraminfo=[]
for i in range(a.numParams):
 bb=C.create_string_buffer(256);d(8,i=i,p=C.cast(bb,ptr));paraminfo.append((i,bb.value.decode('latin1'),round(getter(e,i),3)))
print('PARAMETERS',paraminfo,flush=True)
setter=C.CFUNCTYPE(None,C.POINTER(AEffect),ip,C.c_float)(a.setParameter)
def params():
 for k,v in plan.get('parameters',{}).items():setter(e,int(k),float(v))
params()
proc=Process(a.processReplacing or a.process)
outs=[(C.c_float*BLOCK)() for _ in range(max(2,a.numOutputs))];ins=[(C.c_float*BLOCK)() for _ in range(max(1,a.numInputs))]
op=(C.POINTER(C.c_float)*len(outs))(*[C.cast(b,C.POINTER(C.c_float)) for b in outs]);inp=(C.POINTER(C.c_float)*len(ins))(*[C.cast(b,C.POINTER(C.c_float)) for b in ins])
frames=int(duration*SR);bytesize=frames*8
Path(out).parent.mkdir(parents=True,exist_ok=True)
with open(out,'wb') as f:
 f.write(struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',bytesize+36,b'WAVE',b'fmt ',16,3,2,SR,SR*8,8,32,b'data',bytesize))
 for start in range(0,frames,BLOCK):
  timeinfo.samplePos=start;timeinfo.ppqPos=start/SR*112/60
  msg=[]
  while cursor<len(midi) and int(midi[cursor][0]*SR)<start+BLOCK:
   t,status,b1,b2=midi[cursor];cursor+=1
   if status&0xf0==0xc0:d(2,v=b1);params();continue
   mm=Midi();mm.type=1;mm.byteSize=32;mm.deltaFrames=max(0,int(t*SR)-start);mm.midiData[:]=[status,b1,b2,0];msg.append(mm)
  if msg:
   ev=Events();ev.numEvents=len(msg)
   for i,mm in enumerate(msg):ev.events[i]=C.addressof(mm)
   d(25,p=C.cast(C.pointer(ev),ptr))
  for ob in outs:C.memset(ob,0,BLOCK*4)
  proc(e,inp,op,BLOCK)
  count=min(BLOCK,frames-start);l=array.array('f');l.frombytes(bytes(outs[0]));r=array.array('f');r.frombytes(bytes(outs[1 if a.numOutputs>1 else 0]));inter=array.array('f',[0.])*(count*2);inter[::2]=l[:count];inter[1::2]=r[:count];f.write(inter.tobytes())
  if start%(SR*10//BLOCK*BLOCK)==0:print(round(start/SR),'/',round(duration),flush=True)
d(72);d(12,v=0);d(1)
print('DONE',flush=True)
