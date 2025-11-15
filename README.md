XArm Planner ROS2 Package

Este repositorio contiene los nodos, launch files y scripts necesarios para controlar un brazo xArm6 tanto en simulación como en el robot real, junto con la interfaz gráfica de control.

Requisitos

ROS2 (ej. Humble o la distribución que estés usando)

Dependencias de xarm_planner y xarm_gui

Python 3.8+

C++17 compatible (para la compilación de nodos)

Instalación

Clona el repositorio en tu workspace de ROS2:

cd ~/dev_ws/src
git clone <URL_DEL_REPOSITORIO>


Construye el workspace:

cd ~/dev_ws
colcon build
source install/setup.bash

Uso
1️⃣ Lanzar el nodo del planificador xArm6

Dependiendo de si quieres usar el simulador o el robot real:

Simulado:

ros2 launch xarm_planner xarm6_planner_fake.launch.py add_gripper:=true


Robot real:

ros2 launch xarm_planner xarm6_planner_realmove.launch.py robot_ip:=192.168.1.117 add_gripper:=true


Ajusta robot_ip según la IP de tu brazo real.

2️⃣ Lanzar el nodo de planificación de emergencias / control adicional
ros2 launch xarm_planner emer_planner.launch.py dof:=6 robot_type:=xarm


Cambia dof y robot_type si usas otra configuración.

3️⃣ Lanzar la interfaz gráfica
ros2 run xarm_gui gui_pose_publisher


Esto permite enviar poses al brazo mediante GUI.

Notas importantes

Todos los nodos ROS2 deben correr en el mismo workspace y con source install/setup.bash activado.

Si usas el brazo real, asegúrate de que no haya obstáculos y que el gripper esté correctamente configurado.

El nodo emer_planner permite ejecutar trayectorias predefinidas (círculo, cuadrado, etc.) y puede recibir comandos stop para cancelar la ejecución.

Comandos disponibles por topic

/xarm/shape_command (std_msgs/msg/String):

"circle" → Ejecuta trayectoria circular

"square" → Ejecuta trayectoria cuadrada

"stop" → Detiene la ejecución en curso

/xarm/shape_status (std_msgs/msg/String):

Mensajes de estado del brazo (ej. "circle completed", "Robot busy, ignore command")
