import  io
import PIL.Image
import os,sys
import psutil


if sys.platform == 'win32':
    import win32api
    import win32gui
    import win32con
    import win32ui

def kill_by_name(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            proc.terminate()

def is_process_running(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return True
    return False

def get_win32_default_icon():
    """
    Get the default icon for the current system.
    """
    # Get the default icon
    ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
    ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hbmp = win32ui.CreateBitmap()
    hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
    hdc = hdc.CreateCompatibleDC()
    hdc.SelectObject(hbmp)
    hdc.DrawIcon((0, 0), win32gui.LoadIcon(0, win32con.IDI_APPLICATION))
    hbmp.GetBitmapBits(True)
    im = PIL.Image.frombuffer("RGBA", (ico_x, ico_y), hbmp.GetBitmapBits(True), "raw", "BGRA", 0, 1)
    im = im.resize((16,16),PIL.Image.LANCZOS)
    icobytes = io.BytesIO()
    im.save(icobytes, format='PNG')
    im.close()
    return icobytes.getvalue()

def get_default_icon():
    pngbytes = io.BytesIO()
    PIL.Image.open('exe-icon-32.png').save(pngbytes, format='PNG')
    return pngbytes.getvalue()

def get_exe_icon(exe_path):
    if sys.platform != 'win32':
        return get_default_icon()
    try:
        large, small = win32gui.ExtractIconEx(exe_path, 0)
    except:
        return get_win32_default_icon()
    win32gui.DestroyIcon(large[0])
#    win32gui.ExtractIconEx(exe_path, 0, 1)
    ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
    #creating a destination memory DC
    hdc = win32ui.CreateDCFromHandle( win32gui.GetDC(0) )
    hbmp = win32ui.CreateBitmap()
    hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_x)
    hdc = hdc.CreateCompatibleDC()    
    hdc.SelectObject(hbmp)
    #draw a icon in it
    hdc.DrawIcon( (0,0), small[0] )
    win32gui.DestroyIcon(small[0])
    #tempDirectory = os.environ['TEMP']
    #convert picture
    hbmp.GetBitmapBits(True)
    #hbmp.SaveBitmapFile( hdc, tempDirectory + "\Icontemp.bmp")
    im = PIL.Image.frombuffer("RGBA", (ico_x,ico_x), hbmp.GetBitmapBits(True), "raw", "BGRA", 0, 1)
    #im = PIL.Image.open(tempDirectory + "\Icontemp.bmp")
    icobytes = io.BytesIO()
    im = im.resize((16,16),PIL.Image.LANCZOS)
    im.save(icobytes,format='PNG')
    im.close()
    #os.startfile(tempDirectory + "\Icontemp.bmp")
    #os.remove(tempDirectory + "\Icontemp.bmp")
    return icobytes.getvalue()


if __name__ == '__main__':

    exe_path = "D:\APPS\Symenu\ProgramFiles\SPSSuite\SyMenuSuite\Everything_(x64)_sps\Everything.exe"
    icon_path = os.path.basename(exe_path) + ".png"
    icobytes = get_exe_icon(exe_path)
    icofile = open(icon_path, 'wb')
    icofile.write (icobytes)
    icofile.close()
    icodir = os.getcwd()
    print(icodir)
    os.startfile(icodir)
    
    #os.startfile(icon_path)
