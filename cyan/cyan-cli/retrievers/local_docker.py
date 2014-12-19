import pprint
from docker import Client as DockerClient
from fnmatch import fnmatch

docker = DockerClient(base_url='unix://var/run/docker.sock')

def get_host_port(container_info, container_port):
    try:
        host_port = container_info['HostConfig']['PortBindings']['%s/tcp' % container_port][0]['HostPort']
    except KeyError:
        open_ports = '\n'.join(container_info['HostConfig']['PortBindings'].keys())
        raise Exception('Port %s is not open on container. \n'
                        'Ports on container: \n %s' % (container_port, open_ports))
    return host_port


def get_name(container_info):
    return container_info['Name'].lstrip('/')

def ls(glob, port):
    all_containers = docker.containers()
    matched = [c for c in all_containers if fnmatch(c['Image'], glob)]
    return {c['Names'][-1][1:]: {
        'addr': ['%s:%s' % (m['IP'], m['PublicPort']) for m in c['Ports']  if m['PrivatePort'] == int(port)][0]
    } for c in matched}

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('glob')
    parser.add_argument('port')
    args = parser.parse_args()
    pprint.pprint(ls(args.glob, args.port))
