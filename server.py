import socket
import _thread


from models.base_model import SQLModel
from request import Request
from utils import log


from routes import error


from routes.routes_weibo import route_dict as weibo_routes
from routes.routes_user import route_dict as user_routes
from routes.routes_public import route_dict as public_routes


def response_for_path(request):
    """
    根据 path 调用相应的处理函数
    没有处理的 path 会返回 404
    """
    r = {}
    # 注册外部的路由
    r.update(weibo_routes())
    r.update(user_routes())
    r.update(public_routes())
    response = r.get(request.path, error)
    log('request path <{}> ------> route <{}>'.format(request.path, response.__name__))
    return response(request)


def request_from_connection(connection):
    request = b''
    buffer_size = 1024
    while True:
        r = connection.recv(buffer_size)
        request += r
        # 取到的数据长度不够 buffer_size 的时候，说明数据已经取完了。
        if len(r) < buffer_size:
            request = request.decode()
            # log('request\n {}'.format(request))
            return request


def process_request(connection):
    with connection:
        r = request_from_connection(connection)
        # log('request log:\n <{}>'.format(r))
        # 把原始请求数据传给 Request 对象
        request = Request(r)
        # 用 response_for_path 函数来得到 path 对应的响应内容
        response = response_for_path(request)
        # log("response log:\n <{}>".format(response))
        # 把响应发送给客户端
        connection.sendall(response)


def run(host, port):
    """
    启动服务器
    """
    # 初始化 ORM
    SQLModel.init_db()
    log('数据库链接初始化 <{}>'.format(SQLModel.connection.host_info))
    log('开始运行于', 'http://{}:{}'.format(host, port))
    with socket.socket() as s:
        s.bind((host, port))
        # 监听 接受 读取请求数据 解码成字符串
        s.listen()
        # 无限循环来处理请求
        while True:
            connection, address = s.accept()
            # 第二个参数类型必须是 tuple
            # log('ip {}'.format(address))
            _thread.start_new_thread(process_request, (connection,))


if __name__ == '__main__':
    # 生成配置并且运行程序
    config = dict(
        host='127.0.0.1',
        port=3600,
    )
    run(**config)
