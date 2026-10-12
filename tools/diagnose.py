"""Print machine metadata only; never environment values or document content."""
import os
import platform
import shutil
import struct
import sys
import tkinter

print('OS:', platform.platform())
print('Python:', platform.python_version(), f'{struct.calcsize("P")*8}bit')
print('CPU architecture:', platform.machine(), 'logical cores:', os.cpu_count())
print('Tk:', tkinter.TkVersion)
print('Free disk GiB:', round(shutil.disk_usage('.').free / 1024**3, 1))
if sys.platform == 'win32':
    import ctypes
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong),
                    ('total_phys',ctypes.c_ulonglong),('avail_phys',ctypes.c_ulonglong),
                    ('total_page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),
                    ('total_virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),
                    ('avail_extended',ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        print('RAM GiB:', round(status.total_phys / 1024**3, 1))
print('GPU: not used in Phase A')
