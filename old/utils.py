# Utility Functions
import json
import socket
import numpy as np
import uuid


def moving_average(values, window_size):
    if len(values) < window_size:
        return np.mean(values)
    return np.mean(values[-window_size:])

def serialize(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return json.dumps(obj)
    elif isinstance(obj, (list, tuple, set)):
        return json.dumps([serialize(item) for item in obj])
    elif isinstance(obj, dict):
        return json.dumps({k: serialize(v) for k, v in obj.items()})
    else:
        try:
            data = {attr: serialize(getattr(obj, attr)) for attr in dir(obj) if not callable(getattr(obj, attr)) and not attr.startswith("__")}
            return json.dumps(data)
        except TypeError:
            return json.dumps(str(obj))
        
def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def create_effect(effect_class, *args, **kwargs):
    """Создаёт экземпляр эффекта с уникальным ID."""
    effect = effect_class(*args, **kwargs)
    effect_id = str(uuid.uuid4())  # Генерируем уникальный ID для эффекта
    return effect, effect_id
