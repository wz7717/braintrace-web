"""Render client-owned file downloads without a shared server media endpoint."""
import base64
import html

def local_download(data,filename,label):
    content=data.encode('utf-8') if isinstance(data,str) else data
    encoded=base64.b64encode(content).decode('ascii')
    return ('<a id="download" style="font:16px sans-serif;color:#087f8c" download="'
        +html.escape(filename,quote=True)+'">'+html.escape(label)+'</a>'
        +'<script>const bytes=Uint8Array.from(atob("'+encoded+'"),c=>c.charCodeAt(0));'
        +'const url=URL.createObjectURL(new Blob([bytes],{type:"application/octet-stream"}));'
        +'document.getElementById("download").href=url;'
        +'addEventListener("unload",()=>URL.revokeObjectURL(url));</script>')
