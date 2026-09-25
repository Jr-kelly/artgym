import ctypes as c,json,os
class App(c.Structure):_fields_=[('sType',c.c_uint32),('pNext',c.c_void_p),('name',c.c_char_p),('version',c.c_uint32),('engine',c.c_char_p),('engineVersion',c.c_uint32),('apiVersion',c.c_uint32)]
class Info(c.Structure):_fields_=[('sType',c.c_uint32),('pNext',c.c_void_p),('flags',c.c_uint32),('app',c.POINTER(App)),('layers',c.c_uint32),('layerNames',c.c_void_p),('extensions',c.c_uint32),('extensionNames',c.c_void_p)]
class Queue(c.Structure):_fields_=[('flags',c.c_uint32),('count',c.c_uint32),('timestamp',c.c_uint32),('extent',c.c_uint32*3)]
out={'host':os.uname().nodename,'operation':'Read-only Vulkan device/queue enumeration; no simulator'}
try:
 lib=c.CDLL('libvulkan.so.1')
 lib.vkCreateInstance.argtypes=[c.POINTER(Info),c.c_void_p,c.POINTER(c.c_void_p)];lib.vkCreateInstance.restype=c.c_int32
 app=App(0,None,b'artgym-diagnostic',0,b'none',0,1<<22);info=Info(1,None,0,c.pointer(app),0,None,0,None);instance=c.c_void_p()
 result=lib.vkCreateInstance(c.byref(info),None,c.byref(instance));out['create_result']=result
 if result==0:
  lib.vkEnumeratePhysicalDevices.argtypes=[c.c_void_p,c.POINTER(c.c_uint32),c.POINTER(c.c_void_p)];lib.vkEnumeratePhysicalDevices.restype=c.c_int32
  n=c.c_uint32();out['enumerate_result']=lib.vkEnumeratePhysicalDevices(instance,c.byref(n),None);out['count']=n.value
  devices=(c.c_void_p*n.value)();lib.vkEnumeratePhysicalDevices(instance,c.byref(n),devices)
  lib.vkGetPhysicalDeviceProperties.argtypes=[c.c_void_p,c.c_void_p]
  lib.vkGetPhysicalDeviceQueueFamilyProperties.argtypes=[c.c_void_p,c.POINTER(c.c_uint32),c.POINTER(Queue)]
  out['devices']=[]
  for i,device in enumerate(devices):
   props=c.create_string_buffer(8192);lib.vkGetPhysicalDeviceProperties(device,props);name=bytes(props)[20:276].split(b'\0',1)[0].decode(errors='replace')
   count=c.c_uint32();lib.vkGetPhysicalDeviceQueueFamilyProperties(device,c.byref(count),None);queues=(Queue*count.value)();lib.vkGetPhysicalDeviceQueueFamilyProperties(device,c.byref(count),queues)
   out['devices'].append({'index':i,'name':name,'queues':[{'flags':v.flags,'count':v.count,'graphics':bool(v.flags&1),'compute':bool(v.flags&2)} for v in queues]})
  lib.vkDestroyInstance.argtypes=[c.c_void_p,c.c_void_p];lib.vkDestroyInstance(instance,None)
except Exception as exc:out['error']=repr(exc)
print(json.dumps(out))

