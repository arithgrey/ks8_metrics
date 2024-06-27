from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configuración del cliente de Kubernetes
config.load_kube_config()

# Inicializar API de Métricas y Core
metrics_api = client.CustomObjectsApi()
core_api = client.CoreV1Api()

# Namespaces a consultar
namespaces = ["core", "new-core", "app-new-core"]

# Función para obtener métricas de consumo de recursos y especificaciones de recursos
def get_metrics_and_specs_for_namespace(namespace):
    result_lines = []

    try:
        # Obtener métricas de pods en el namespace
        pod_metrics = metrics_api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods"
        )
        
        # Obtener especificaciones de pods en el namespace
        pods = core_api.list_namespaced_pod(namespace)

        pod_specs = {pod.metadata.name: pod for pod in pods.items}
        
        for pod_metric in pod_metrics['items']:
            pod_name = pod_metric['metadata']['name']

            if pod_name in pod_specs:
                pod_spec = pod_specs[pod_name]
                for container_metric in pod_metric['containers']:
                    container_name = container_metric['name']
                    cpu_usage = container_metric['usage']['cpu']
                    memory_usage = container_metric['usage']['memory']
                    
                    for container_spec in pod_spec.spec.containers:
                        if container_spec.name == container_name:
                            cpu_requested = container_spec.resources.requests.get('cpu', 'None')
                            cpu_limit = container_spec.resources.limits.get('cpu', 'None')
                            memory_requested = container_spec.resources.requests.get('memory', 'None')
                            memory_limit = container_spec.resources.limits.get('memory', 'None')

                            # Calcular y mostrar el uso de memoria en relación con lo solicitado
                            memory_requested_value = parse_memory_string(memory_requested)
                            memory_used_value = parse_memory_string(memory_usage)
                            
                            if memory_requested_value != 0:
                                memory_usage_ratio = (memory_used_value / memory_requested_value) * 100
                            else:
                                memory_usage_ratio = 0

                            # Preparar la línea para el archivo CSV
                            result_line = f"{namespace},{pod_name},{container_name},{cpu_usage},{memory_usage},{cpu_requested},{cpu_limit},{memory_requested},{memory_limit},{memory_usage_ratio:.2f}%\n"
                            result_lines.append(result_line)

            else:
                print(f"  Pod {pod_name} not found in spec API response")

    except ApiException as e:
        print(f"Exception when calling API: {e}")

    return result_lines

# Función para convertir cadenas de memoria a bytes
def parse_memory_string(memory_str):
    multipliers = {
        "Ki": 1024,
        "Mi": 1024 ** 2,
        "Gi": 1024 ** 3,
        "Ti": 1024 ** 4,
        "Pi": 1024 ** 5,
        "K": 1,
        "M": 10 ** 3,
        "G": 10 ** 6,
        "T": 10 ** 9,
        "P": 10 ** 12,
    }
    for suffix, multiplier in multipliers.items():
        if memory_str.endswith(suffix):
            return int(float(memory_str[:-len(suffix)]) * multiplier)
    return int(memory_str)

# Nombre del archivo de salida
output_file = "kubernetes_metrics.csv"

# Obtener métricas y especificaciones para cada namespace
with open(output_file, 'w') as file:
    # Escribir encabezado del archivo CSV
    file.write("Namespace,Nombre del Pod,Nombre del Contenedor,Uso de CPU,Uso de Memoria,CPU Solicitada,CPU Límite,Memoria Solicitada,Memoria Límite,Ratio de Uso de Memoria (%)\n")
    
    for ns in namespaces:
        lines = get_metrics_and_specs_for_namespace(ns)
        for line in lines:
            file.write(line)

print(f"Archivo CSV generado: {output_file}")
