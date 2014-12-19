from flask import Flask, Response, request
import os
import logging

app = Flask(__name__)

@app.route('/')
def index():
    c = '%s' % str(request.cookies)
    
    resp = Response('<html style="background:%s">%s</html>' % (os.getenv('color'), c))
    resp.set_cookie('sessionid',value=os.getenv('color'))
    return resp

@app.route('/health/<status>')
def set_health(status):
    with open('/health', 'w+') as f:
         f.write(status)
    return 'ok', 200
@app.route('/health')
def get_health():
    try:
        with open('/health') as f:
             health = f.read().strip()
             return Response(status=204 if health == 'good' else 500)
    except:
        return 'problem', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0',threaded=True,debug=True)

