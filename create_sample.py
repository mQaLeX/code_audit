import os
import sys
import tempfile
import shutil


def create_sample_vulnerable_code():
    """
    创建包含漏洞的示例代码
    """
    sample_dir = tempfile.mkdtemp(prefix="vulnerable_code_")
    
    web_app_code = '''from flask import Flask, request, render_template_string
import sqlite3

app = Flask(__name__)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return "Login successful"
    else:
        return "Login failed"

@app.route('/search')
def search():
    query = request.args.get('q', '')
    
    template = f"<h1>Search Results</h1><p>You searched for: {query}</p>"
    return render_template_string(template)

@app.route('/exec')
def exec_command():
    cmd = request.args.get('cmd', 'ls')
    output = os.popen(cmd).read()
    return output

if __name__ == '__main__':
    app.run(debug=True)
'''
    
    cli_app_code = '''import click
import os
import subprocess

@click.command()
@click.option('--file', help='File to process')
@click.option('--command', help='Command to execute')
def cli(file, command):
    if file:
        with open(file, 'r') as f:
            content = f.read()
            print(content)
    
    if command:
        result = subprocess.run(command, shell=True, capture_output=True)
        print(result.stdout.decode())

@click.command()
@click.argument('path')
def read_file(path):
    with open(path, 'r') as f:
        print(f.read())

if __name__ == '__main__':
    cli()
'''
    
    with open(os.path.join(sample_dir, 'web_app.py'), 'w') as f:
        f.write(web_app_code)
    
    with open(os.path.join(sample_dir, 'cli_app.py'), 'w') as f:
        f.write(cli_app_code)
    
    return sample_dir


if __name__ == '__main__':
    print("创建示例漏洞代码...")
    sample_dir = create_sample_vulnerable_code()
    
    print(f"示例代码已创建在: {sample_dir}")
    print()
    print("可以使用以下命令进行测试：")
    print(f"python main.py {sample_dir} python web")
    print(f"python main.py {sample_dir} python cli")
    print()
    print("测试完成后，可以手动删除该目录")
