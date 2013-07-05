

from boto.ec2.connection import EC2Connection
from settings.conf.awscredential import AWS_ACCESS_ID, AWS_KEY

def ec2_connect(aws_access_key=None, aws_secret_key=None):
    if not aws_access_key:
        aws_access_key = AWS_ACCESS_ID
    if not aws_secret_key:
        aws_secret_key = AWS_KEY

    return EC2Connection(aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key)



def get_acl(ec2_conn, ports=None, group_names=None):
    all_ips = []
    security_groups = ec2_conn.get_all_security_groups(groupnames=group_names)        
    for security_group in security_groups:
        for rule in security_group.rules:
            if rule.from_port == ports[0] and rule.to_port = ports[1]:
                all_ips.append(rule)        
            
    return all_ips
