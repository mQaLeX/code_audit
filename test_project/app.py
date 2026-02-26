from flask import Flask, request, render_template_string
import os

app = Flask(__name__)


@app.route('/')
def index():
    return '''
    <h1>测试应用 - 漏洞演示</h1>
    <ul>
        <li><a href="/ping">Ping测试 (命令注入)</a></li>
        <li><a href="/read">文件读取 (任意文件读)</a></li>
        <li><a href="/exec">命令执行 (命令注入)</a></li>
    </ul>
    '''


@app.route('/ping')
def ping():
    """
    命令注入漏洞
    使用os.popen执行用户输入的命令
    """
    host = request.args.get('host', '127.0.0.1')
    count = request.args.get('count', '1')
    
    command = f"ping -c {count} {host}"
    
    try:
        output = os.popen(command).read()
        return f'''
        <h2>Ping测试</h2>
        <p>执行的命令: {command}</p>
        <pre>{output}</pre>
        <p><a href="/">返回首页</a></p>
        '''
    except Exception as e:
        return f"错误: {str(e)}"


@app.route('/read')
def read_file():
    """
    任意文件读取漏洞
    直接读取用户指定的文件路径
    """
    filename = request.args.get('file', 'README.md')
    
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        return f'''
        <h2>文件内容</h2>
        <p>文件名: {filename}</p>
        <pre>{content}</pre>
        <p><a href="/">返回首页</a></p>
        '''
    except FileNotFoundError:
        return f"文件不存在: {filename}"
    except Exception as e:
        return f"错误: {str(e)}"


@app.route('/exec')
def exec_command():
    """
    命令注入漏洞
    使用os.system执行用户输入的命令
    """
    cmd = request.args.get('cmd', 'ls -la')
    
    try:
        os.system(cmd)
        return f'''
        <h2>命令执行</h2>
        <p>执行的命令: {cmd}</p>
        <p>命令已执行</p>
        <p><a href="/">返回首页</a></p>
        '''
    except Exception as e:
        return f"错误: {str(e)}"


@app.route('/search')
def search():
    """
    命令注入漏洞
    使用grep搜索用户输入的内容
    """
    pattern = request.args.get('q', '')
    
    command = f"grep -r '{pattern}' ."
    
    try:
        output = os.popen(command).read()
        return f'''
        <h2>搜索结果</h2>
        <p>搜索内容: {pattern}</p>
        <pre>{output}</pre>
        <p><a href="/">返回首页</a></p>
        '''
    except Exception as e:
        return f"错误: {str(e)}"


@app.route('/download')
def download_file():
    """
    任意文件读取漏洞
    下载用户指定的文件
    """
    filepath = request.args.get('path', 'README.md')
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        return content, 200, {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': f'attachment; filename={os.path.basename(filepath)}'
        }
    except FileNotFoundError:
        return f"文件不存在: {filepath}", 404
    except Exception as e:
        return f"错误: {str(e)}", 500


@app.route('/log')
def view_log():
    """
    任意文件读取漏洞
    查看日志文件
    """
    log_file = request.args.get('file', 'app.log')
    
    try:
        with open(log_file, 'r') as f:
            content = f.read()
        
        return f'''
        <h2>日志文件</h2>
        <p>日志文件: {log_file}</p>
        <pre>{content}</pre>
        <p><a href="/">返回首页</a></p>
        '''
    except FileNotFoundError:
        return f"日志文件不存在: {log_file}"
    except Exception as e:
        return f"错误: {str(e)}"


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
