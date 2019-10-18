from neo4j import GraphDatabase
from datetime import datetime
from datetime import timedelta


def calculate_date(time, shipment_day, actual_time, hours_need):
    if (shipment_day.hour < 8):
        shipment_day = datetime(shipment_day.year, shipment_day.month, shipment_day.day, 8, 0, 0)

    if (shipment_day.hour + hours_need >= 24 and hours_need < 24):
        shipment_day = shipment_day + timedelta(minutes=time)
        max_time_package = datetime(actual_time.year, actual_time.month, actual_time.day, 23, 59, 59)
        difference_delivery_hours = shipment_day - max_time_package
        shipment_day = datetime(shipment_day.year, shipment_day.month, shipment_day.day, 8, 0,
                                0) + difference_delivery_hours
    elif (shipment_day.hour + hours_need < 24):
        shipment_day = shipment_day + timedelta(minutes=time)
    elif (hours_need > 24):
        shipment_day = shipment_day + timedelta(minutes=time) + timedelta(
            hours=8 * (shipment_day.day - actual_time.day))

    if (shipment_day.hour < 8):
        shipment_day = shipment_day + timedelta(hours=8)

    return shipment_day


class Shipments(object):
    neo_connection = None

    def __init__(self, neo_driver):
        self.neo_connection = neo_driver.session()

    def shipping_manage(self, shipment_method, product, destination_city):

        message_values_list = self.search_warehouses(product)

        if (len(message_values_list) is 0):
            print('El producto seleccionado no se puede comprar')
            return None

        supplier_name = message_values_list[0][0]
        warehouses = []
        for warehouse in message_values_list:
            warehouses.append(warehouse[1])

        if (('A_' + destination_city) in warehouses):
            print('El paquete está en su destino')
            return None

        if (shipment_method is 1):
            message_values_list = self.shipment_method_1(warehouses, destination_city)
        elif (shipment_method is 2):
            message_values_list = self.shipment_method_2(warehouses, destination_city)
        elif (shipment_method is 3):
            message_values_list = self.shipment_method_3(warehouses, destination_city)
        else:
            print('Tipo de envio no valido')
            return None

        if (message_values_list is None or len(message_values_list) is 0):
            print('No se ha encontrado una ruta optima para llegar a su destino')
            return None

        message_values_list[0].append(supplier_name)
        message_values_list[0].append(shipment_method)
        message_values_list[0].append(product)

        actual_time = datetime.today()
        shipment_day = actual_time + timedelta(hours=1)
        hours_need = message_values_list[0][3] / 60

        shipment_day = calculate_date(message_values_list[0][3], shipment_day, actual_time, hours_need)

        print('Dia de entrega: ' + str(shipment_day))

        return message_values_list

    def shipment_method_1(self, warehouses, destination_city):
        actual_time = datetime.today()
        if (actual_time.hour >= 19):
            print('Se ha acabado el servicio de entrega por hoy, pruebe otro tipo de pedido')
            return None
        elif (actual_time.hour < 8):
            max_time = datetime(actual_time.year, actual_time.month, actual_time.day, 19, 0, 0)
            starts_time = datetime(actual_time.year, actual_time.month, actual_time.day, 8, 0, 0)
            time_difference = max_time - starts_time - timedelta(hours=1)  # 1 h de empaquetado
            minutes_difference = time_difference / timedelta(minutes=1)
        else:
            max_time = datetime(actual_time.year, actual_time.month, actual_time.day, 19, 0, 0)
            time_difference = max_time - actual_time - timedelta(hours=1)  # 1 h empaquetado
            minutes_difference = time_difference / timedelta(minutes=1)

        message = self.neo_connection.run("match path_almacen = (al:almacen)-[u:union_almacen]->(b:ciudad) "
                                          "where al.nombre = $warehouse_1 or al.nombre = $warehouse_2 "
                                          "with b.nombre as ciudad_origen "
                                          "MATCH path = (b:ciudad)-[*1..4]->(c:ciudad) "
                                          "WHERE b.nombre = ciudad_origen AND c.nombre = $destination_city "
                                          "with reduce(acc = 0, n in relationships(path)|acc + n.coste) as resultCoste, "
                                          "reduce(acc = 0, n in relationships(path)|acc + n.tiempo + n.tiempo_carga_descarga) as resultTime, "
                                          "extract(t in relationships(path)|type(t)) as vehicles ,[ciudades in nodes(path) | ciudades.nombre] as noodes, "
                                          "[relaciones in relationships(path) | relaciones.tiempo + relaciones.tiempo_carga_descarga] as relations "
                                          "where resultTime < $minutes_difference "
                                          "return noodes,vehicles,relations,resultTime,resultCoste "
                                          "order by resultCoste limit 1", destination_city=destination_city,
                                          warehouse_1=warehouses[0], warehouse_2=warehouses[1],
                                          minutes_difference=minutes_difference)

        return message.values()

    def shipment_method_2(self, warehouses, destination_city):
        actual_time = datetime.today()
        next_day_time = actual_time + timedelta(days=1)
        next_day_time = datetime(next_day_time.year, next_day_time.month, next_day_time.day, 14, 0, 0)
        time_difference = next_day_time - actual_time - timedelta(hours=8) - timedelta(
            hours=1)  # tiempo entre las 0 y 8h y el tiempo que tarda en empaquetarse 1 h
        minutes_difference = time_difference / timedelta(minutes=1)

        message = self.neo_connection.run("match path_almacen = (al:almacen)-[u:union_almacen]->(b:ciudad) "
                                          "where al.nombre = $warehouse_1 or al.nombre = $warehouse_2 "
                                          "with b.nombre as ciudad_origen "
                                          "MATCH path = (b:ciudad)-[*1..4]->(c:ciudad) "
                                          "WHERE b.nombre = ciudad_origen AND c.nombre = $destination_city "
                                          "with reduce(acc = 0, n in relationships(path)|acc + n.coste) as resultCoste, "
                                          "reduce(acc = 0, n in relationships(path)|acc + n.tiempo + n.tiempo_carga_descarga) as resultTime, "
                                          "extract(t in relationships(path)|type(t)) as vehicles ,[ciudades in nodes(path) | ciudades.nombre] as noodes, "
                                          "[relaciones in relationships(path) | relaciones.tiempo + relaciones.tiempo_carga_descarga] as relations "
                                          "where resultTime < $minutes_difference "
                                          "return noodes,vehicles,relations,resultTime,resultCoste "
                                          "order by resultCoste limit 1", destination_city=destination_city,
                                          warehouse_1=warehouses[0], warehouse_2=warehouses[1],
                                          minutes_difference=minutes_difference)

        return message.values()

    def shipment_method_3(self, warehouses, destination_city):

        message = self.neo_connection.run("match path_almacen = (al:almacen)-[u:union_almacen]->(b:ciudad) "
                                          "where al.nombre = $warehouse_1 or al.nombre = $warehouse_2 "
                                          "with b.nombre as ciudad_origen "
                                          "MATCH path = (b:ciudad)-[*1..4]->(c:ciudad) "
                                          "WHERE b.nombre = ciudad_origen AND c.nombre = $destination_city "
                                          "with reduce(acc = 0, n in relationships(path)|acc + n.coste) as resultCoste, "
                                          "reduce(acc = 0, n in relationships(path)|acc + n.tiempo + n.tiempo_carga_descarga) as resultTime, "
                                          "extract(t in relationships(path)|type(t)) as vehicles ,[ciudades in nodes(path) | ciudades.nombre] as noodes, "
                                          "[relaciones in relationships(path) | relaciones.tiempo + relaciones.tiempo_carga_descarga] as relations "
                                          "return noodes,vehicles,relations,resultTime,resultCoste "
                                          "order by resultCoste LIMIT 1", destination_city=destination_city,
                                          warehouse_1=warehouses[0], warehouse_2=warehouses[1])

        return message.values()

    def search_warehouses(self, product):

        message = self.neo_connection.run("MATCH (p:proveedor)-[u:union_proveedor]-(al:almacen) "
                                          "where $product IN p.productos "
                                          "with p.nombre as nombre_proveedor, al.nombre as almacen "
                                          "return nombre_proveedor, almacen", product=product)
        return message.values()


class BDDD_Conection(object):
    neo_connection = None

    def __init__(self, neo_driver):
        self.neo_connection = neo_driver.session()

    def load_database(self, BBDD_path):
        self.delete_database()
        bbdd = open(BBDD_path, "r", encoding="utf-8")
        self.neo_connection.run(bbdd.read())

    def delete_database(self):
        self.neo_connection.run("MATCH (n) DETACH DELETE n")

    def set_load_unload_time(self):
        self.neo_connection.run("MATCH p=()-[r:maritimo]->() set r.tiempo_carga_descarga = 40")
        self.neo_connection.run("MATCH p=()-[r:aereo]->() set r.tiempo_carga_descarga = 80")
        self.neo_connection.run("MATCH p=()-[r:ferrocarril]->() set r.tiempo_carga_descarga = 20")
        self.neo_connection.run("MATCH p=()-[r:carretera]->() set r.tiempo_carga_descarga = 10")


class Package(object):
    neo_connection = None

    def __init__(self, neo_driver, message_values_list):
        self.neo_connection = neo_driver.session()
        self.cities = message_values_list[0][0]
        self.vehicles = message_values_list[0][1]
        self.city_times = message_values_list[0][2]
        self.total_time = message_values_list[0][3]
        self.total_cost = message_values_list[0][4]
        self.suplier_name = message_values_list[0][5]
        self.shipment_method = message_values_list[0][6]
        self.product = message_values_list[0][7]

        self.create_package()
        self.update_suplier_departure()

    def create_package(self):
        message = self.neo_connection.run(
            "Create (p:paquete{producto:$product,tipo_de_envio:$shipment_method,ruta:$routes, "
            "vehicles:$vehicles,relaciones_tiempo:$city_times,tiempo_total:$total_time,coste_total:$total_cost, "
            "suplier_name:$suplier_name, entregado:'NO'}) "
            "MERGE (v:vehicle{nombre:$first_vehicle,ruta:$routes}) "
            "CREATE (p)-[n:es_llevado_por]->(v) "
            "MERGE (c:ciudad{nombre:$origin_city}) "
            "MERGE (v)-[h:esta_en]->(c) Return id(p)", origin_city=self.cities[0], product=self.product,
            routes=self.cities, shipment_method=self.shipment_method, vehicles=self.vehicles,
            city_times=self.city_times, total_time=self.total_time, total_cost=self.total_cost,
            first_vehicle=self.vehicles[0], suplier_name=self.suplier_name)

        self.id_package = message.values()[0][0]
        print('Se ha creado el paquete de tipo ' + str(self.shipment_method) + ': estamos en ' + self.cities[
            0] + ' por via ' + self.vehicles[0] + ' con destino final ' + self.cities[-1])

    def update_suplier_departure(self):
        self.neo_connection.run("match (p:proveedor{nombre:$suplier_name}) "
                                "set p.envios_sin_entregar = p.envios_sin_entregar + 1, "
                                "p.facturacion_por_abonar = p.facturacion_por_abonar + $total_cost",
                                suplier_name=self.suplier_name, total_cost=self.total_cost)

    def update_suplier_arrival(self):
        self.neo_connection.run("match (p:proveedor{nombre:$suplier_name}) "
                                "set p.envios_sin_entregar = p.envios_sin_entregar - 1, "
                                "p.envios_realizados = p.envios_realizados + 1, "
                                "p.facturacion = p.facturacion + $cost, "
                                "p.facturacion_por_abonar = p.facturacion_por_abonar - $cost",
                                suplier_name=self.suplier_name, cost=self.total_cost)

    def update_package_arrival(self):
        self.neo_connection.run("match (p:paquete)-[t:es_llevado_por]->(v:vehicle)"
                                "where id(p) = $id_package "
                                "set p.entregado = 'SI' "
                                "detach delete v", id_package=self.id_package)

    def next_city(self):
        actual_city = self.actual_city()
        next_city = ''
        vehicle_index = 0

        for i in range(0, len(self.cities)):
            if (self.cities[i] == actual_city[0][0]):
                next_city = self.cities[i + 1]
                vehicle_index = i + 1

        if (next_city is self.cities[len(self.cities) - 1]):
            print('El paquete a llegado a su destino: ' + next_city)
            self.update_suplier_arrival()
            self.update_package_arrival()
        else:
            self.neo_connection.run("MATCH (P:paquete)-[u:es_llevado_por]->(v:vehicle) "
                                    "where P.ruta = $route "
                                    "set v.nombre = $new_vehicle "
                                    "with v as vehicle "
                                    "Match path=(vehicle)-[e:esta_en]->(d:ciudad) "
                                    "MERGE (c:ciudad{nombre:$next_city}) "
                                    "MERGE (vehicle)-[h:esta_en]->(c) "
                                    "delete e", next_city=next_city, route=self.cities,
                                    new_vehicle=self.vehicles[vehicle_index])

    def actual_city(self):
        message = self.neo_connection.run("match (p:vehicle)-[e:esta_en]->(c:ciudad) "
                                          "where p.ruta = $cities "
                                          "return c.nombre", cities=self.cities)

        message_values_list = message.values()
        if (len(message_values_list) is 0):
            return None

        return message_values_list

    def where_is_and_time_left(self):
        actual_city = self.actual_city()

        if (actual_city is None):
            print('El paquete ha llegado a su destino')
            return

        sum_index_times = 0
        for i in range(0, len(self.cities)):
            if (self.cities[i] == actual_city[0][0]):
                sum_index_times = i

        time_passed = 0
        for i in reversed(range(sum_index_times)):
            time_passed = time_passed + self.city_times[i]

        actual_time = datetime.today()
        shipment_day = actual_time + timedelta(hours=1)
        hours_need = time_passed / 60

        shipment_day = calculate_date(time_passed, shipment_day, actual_time, hours_need)

        time_total = 0
        for i in range(sum_index_times, len(self.city_times)):
            time_total = time_total + self.city_times[i]

        actual_time = shipment_day
        shipment_day = actual_time
        hours_need = time_total / 60

        shipment_day = calculate_date(time_total, shipment_day, actual_time, hours_need)

        print('El paquete se encuentra en ' + actual_city[0][0] + ' y llegara a su destino el ' + str(shipment_day))


class Info_BDD(object):
    neo_connection = None

    def __init__(self, neo_driver):
        self.neo_connection = neo_driver.session()

    def summary_per_type(self, method_type):
        message = self.neo_connection.run("Match (p:paquete) "
                                          "where p.tipo_de_envio = $method_type "
                                          "return p.suplier_name,p.producto, p.entregado, p.coste_total",
                                          method_type=method_type)

        message_values_list = message.values()

        if (len(message_values_list) is 0):
            print('No existe ningun paquete de ese tipo de envio')
            return None

        print('Hay ' + str(len(message_values_list)) + ' paquetes de tipo ' + str(method_type) + ':')

        for package in message_values_list:
            print('Proveedor: ' + package[0] + '   \tProducto: ' + package[1] + '  \tEntregado: ' + package[
                2] + '\tCoste total:' + str(package[3]))

    def summary_per_suplier(self, suplier_name):
        message = self.neo_connection.run("Match (p:proveedor) "
                                          "where p.nombre = $suplier_name "
                                          "return p.productos, p.facturacion, p.envios_realizados, "
                                          "p.envios_sin_entregar, p.facturacion_por_abonar ", suplier_name=suplier_name)

        message_values_list = message.values()

        print('Proveedor: ' + suplier_name)
        print('Marcas: ' + message_values_list[0][0][0] + ',' + message_values_list[0][0][1] + ',' +
              message_values_list[0][0][2] + ' \tFacturacion: ' + str(
            message_values_list[0][1]) + ' \tFacturacion por abonar: ' + str(
            message_values_list[0][4]) + ' \tEnvios entregados: ' + str(
            message_values_list[0][2]) + ' \tEnvios sin entregar: ' + str(message_values_list[0][3]))

    def summary_packages_per_suplier(self, suplier_name):
        message = self.neo_connection.run("match (p:paquete) "
                                          "where p.suplier_name = $suplier_name "
                                          "return p.tipo_de_envio,p.producto, "
                                          "p.coste_total, p.entregado ", suplier_name=suplier_name)

        message_values_list = message.values()

        if (len(message_values_list) is 0):
            print('El proveedor no ha realizado ningun envio')
            return None

        print('Hay ' + str(len(message_values_list)) + ' paquete realizados por ' + suplier_name + ':')
        for package in message_values_list:
            print('Tipo de envio: ' + str(package[0]) + '   Producto: ' + package[1] + '   \tCoste total: ' + str(
                package[2]) + '  \tEntregado: ' + package[3])


if __name__ == '__main__':
    neo_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("user", "user"))
    BBDD = BDDD_Conection(neo_driver)
    BBDD.load_database("NEO_Database.txt")
    BBDD.set_load_unload_time()
    shipment = Shipments(neo_driver)
    package_list = shipment.shipping_manage(3, 'PUMA', "NY")
    package_list2 = shipment.shipping_manage(2, 'ADIDAS', "Amsterdam")
    package_list3 = shipment.shipping_manage(3, 'NIKE', "NY")
    print('\n')

    if package_list:
        paquete = Package(neo_driver, package_list)
        paquete2 = Package(neo_driver, package_list2)
        paquete3 = Package(neo_driver, package_list3)
        print('\nCiudad en la que esta el paquete 1 y tiempo que le queda para llegar al destino')
        paquete.where_is_and_time_left()

        print('\nMovemos la ciudad del paquete 2')
        paquete.next_city()
        print('Ciudad en la que esta el paquete 2 y tiempo que le queda para llegar al destino')
        paquete2.where_is_and_time_left()

        print('\nMovemos la ciudad del paquete 3')
        paquete3.next_city()
        #paquete3.next_city()
        print('Ciudad en la que esta el paquete 3 y tiempo que le queda para llegar al destino')
        paquete3.where_is_and_time_left()

    info_BDD_manage = Info_BDD(neo_driver)
    print('\n')
    info_BDD_manage.summary_per_type(3)
    print('\n')
    info_BDD_manage.summary_per_suplier('Carrefour')
    print('\n')
    info_BDD_manage.summary_packages_per_suplier('Carrefour')