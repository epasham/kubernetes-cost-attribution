from src import logger_config
from src import prometheus_data
from src import find
from src import cost_assumptions
from src import calculate_cost
from time import sleep

logger = logger_config.logger

def process(promehtheus_info_dict, start_time, end_time):
    """
    Process the billing cycle for this minute

    Returns a list including all of the detailed billing info for this cycle
    """

    # Dict holding the current billing cycles information
    current_billing_cycle_list = []

    # Dict holding the current period's billing information
    kube_pod_info_dict = {}
    kube_node_labels_dict = {}
    kube_pod_container_resource_limits_cpu_cores_dict = {}
    kube_pod_container_resource_limits_memory_bytes_dict = {}

    # Getting the values
    kube_pod_info_dict = prometheus_data.get_kube_pod_info_dict(promehtheus_info_dict, start_time, end_time)
    while kube_pod_info_dict == []:
        sleep(1)
        kube_pod_info_dict = prometheus_data.get_kube_pod_info_dict(promehtheus_info_dict, start_time, end_time)

    sleep(1)

    kube_node_labels_dict = prometheus_data.get_kube_node_labels_dict(promehtheus_info_dict, start_time, end_time)
    while kube_node_labels_dict == []:
        sleep(1)
        kube_node_labels_dict = prometheus_data.get_kube_node_labels_dict(promehtheus_info_dict, start_time, end_time)

    sleep(0.5)

    kube_pod_container_resource_limits_cpu_cores_dict = prometheus_data.get_kube_pod_container_resource_limits_cpu_cores_dict(promehtheus_info_dict, start_time, end_time)
    while kube_pod_container_resource_limits_cpu_cores_dict == []:
        sleep(1)
        kube_pod_container_resource_limits_cpu_cores_dict = prometheus_data.get_kube_pod_container_resource_limits_cpu_cores_dict(promehtheus_info_dict, start_time, end_time)

    sleep(0.5)

    kube_pod_container_resource_limits_memory_bytes_dict = prometheus_data.get_kube_pod_container_resource_limits_memory_bytes_dict(promehtheus_info_dict, start_time, end_time)
    while kube_pod_container_resource_limits_memory_bytes_dict == []:
        sleep(1)
        kube_pod_container_resource_limits_memory_bytes_dict = prometheus_data.get_kube_pod_container_resource_limits_memory_bytes_dict(promehtheus_info_dict, start_time, end_time)

    # Get cost assumption file(s)
    cost_assumptions_dict = cost_assumptions.get()
    #print(cost_assumptions_dict)

    #
    # Loop through the list of pods and calculate how much each pod cost per min
    #
    # Everytime we touch anything in this loop we have to verify the numbers match up to
    # what is calculated in the purple top right section of this spread sheet:
    # https://docs.google.com/spreadsheets/d/1r05JBmegiQ9LiFy9nHixmd2PdFSKp6Bi_a6O-xfRcRw/edit#gid=0
    #
    for pod_row in kube_pod_info_dict:

        print("xxxxxxxxxxxxxxxxxxxx")
        print(pod_row)
        print("xxxxxxxxxxxxxxxxxxxxx")

        if 'node' in pod_row['metric'] and 'exported_namespace' in pod_row['metric'] and 'pod' in pod_row['metric']:

            exported_namespace = pod_row['metric']['exported_namespace']
            node = pod_row['metric']['node']
            pod = pod_row['metric']['pod']

            if (node != ''):

                logger.info("exported_namespace - "+exported_namespace)
                logger.info("node - "+node)
                logger.info("pod - "+pod)

                # Get cpu core limit
                cpu_core_limit = find.pods_resource_limits_cpu_cores(kube_pod_container_resource_limits_cpu_cores_dict,
                                                                    exported_namespace,
                                                                    node,
                                                                    pod)

                # Get memory limit bytes
                memory_bytes_limit = find.pods_resource_limits_memory_bytes(kube_pod_container_resource_limits_memory_bytes_dict,
                                                                   exported_namespace,
                                                                   node,
                                                                   pod)

                # Get machine info dict
                machine_info_dict = find.machine_info_by_hostname(kube_node_labels_dict, node)

                print("============")
                print(node)
                print(kube_node_labels_dict)
                print(machine_info_dict)
                print("============")

                cost_assumptions_memory_percentage = 0.5
                cost_assumptions_cpu_percentage = 0.5
                markup = 0

                if machine_info_dict != None:

                    machine_spot_or_on_demand = None

                    if machine_info_dict['isSpot'] == "true":
                        machine_spot_or_on_demand = 'spot'
                    else:
                        machine_spot_or_on_demand = 'on_demand'

                    logger.info("cpu core limit: "+str(cpu_core_limit))
                    logger.info("memory bytes limit: "+str(memory_bytes_limit))

                    logger.info("machine_spot_or_on_demand: "+machine_spot_or_on_demand)
                    logger.info("machine type: "+machine_info_dict['instance_type'])
                    logger.info("machine hourly cost: "+str(cost_assumptions_dict['ec2_info'][machine_info_dict['instance_type']]['hourly_cost'][machine_spot_or_on_demand]))

                    logger.info("cost_assumptions_dict memory_percentage: "+str(cost_assumptions_memory_percentage))
                    logger.info("cost_assumptions_dict cpu percentage: "+str(cost_assumptions_cpu_percentage))

                    logger.info("machine mark up: "+str(markup))
                    logger.info("ec2 Machine total memory: "+str(cost_assumptions_dict['ec2_info'][machine_info_dict['instance_type']]['memory']))
                    logger.info("ec2 Machine total cpu: "+str(cost_assumptions_dict['ec2_info'][machine_info_dict['instance_type']]['cpu']))

                    current_pod_info = {
                        'namespace': exported_namespace,
                        'start_time': start_time,
                        'end_time': end_time,
                        'node': node,
                        'pod': pod,
                        'memory_bytes_limit': memory_bytes_limit,
                        'cpu_core_limit': cpu_core_limit,
                        'machine_spot_or_on_demand': machine_spot_or_on_demand,
                        'instance_type': machine_info_dict['instance_type'],
                        'instance_hourly_cost': cost_assumptions_dict['ec2_info'][machine_info_dict['instance_type']]['hourly_cost'][machine_spot_or_on_demand],
                        'cost_assumptions_memory_percentage': cost_assumptions_memory_percentage,
                        'cost_assumptions_cpu_percentage': cost_assumptions_cpu_percentage,
                        'instance_markup': markup,
                        'instance_total_memory': cost_assumptions_dict['ec2_info'][machine_info_dict['instance_type']]['memory'],
                        'instance_total_cpu': cost_assumptions_dict['ec2_info'][machine_info_dict['instance_type']]['cpu']
                    }

                    cost_per_min_dict = calculate_cost.get_cost_per_min(
                                            current_pod_info['cost_assumptions_memory_percentage'],
                                            current_pod_info['cost_assumptions_cpu_percentage'],
                                            current_pod_info['instance_hourly_cost'],
                                            current_pod_info['instance_markup'],
                                            current_pod_info['instance_total_memory'],
                                            current_pod_info['instance_total_cpu'],
                                            current_pod_info['memory_bytes_limit'],
                                            current_pod_info['cpu_core_limit']
                                            )

                    logger.info("cost_per_min_dict - total: "+str(cost_per_min_dict['total']))
                    logger.info("cost_per_min_dict - memory: "+str(cost_per_min_dict['memory']))
                    logger.info("cost_per_min_dict - cpu: "+str(cost_per_min_dict['cpu']))

                    # Adding the calculated cost into the dict
                    current_pod_info['cost_per_min_total'] = cost_per_min_dict['total']
                    current_pod_info['cost_per_min_memory'] = cost_per_min_dict['memory']
                    current_pod_info['cost_per_min_cpu'] = cost_per_min_dict['cpu']

                    current_billing_cycle_list.append(current_pod_info)

                    logger.info(current_pod_info)

                    logger.info("###################################################################")

                else:
                    logger.warning("Did not find the node in "+node+" in find.machine_info_by_hostname")

        else:
            logger.warning("Did not find node, exported_namespace, or pod in the dict: pod_row")

    return current_billing_cycle_list
