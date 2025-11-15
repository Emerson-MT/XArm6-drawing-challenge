/* Copyright 2021 UFACTORY Inc. All Rights Reserved.
 *
 * Software License Agreement (BSD License)
 *
 * Author: Vinman <vinman.cub@gmail.com>
 ============================================================================*/

#include "xarm_planner/xarm_planner.h"

#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp> // para tf2::toMsg

#include <cmath>
#include <memory>
#include <vector>
#include <functional>
#include <string>
#include <utility>

#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

#include "xarm_msgs/srv/set_int16.hpp"

// Función para crear target pose a partir de posición y orientación RPY
geometry_msgs::msg::Pose create_target_pose(double x, double y, double z,
                                            double roll, double pitch, double yaw)
{
    geometry_msgs::msg::Pose target_pose;

    // Crear quaternion a partir de roll, pitch y yaw
    tf2::Quaternion q;
    q.setRPY(roll, pitch, yaw);
    q.normalize();

    // Asignar orientación convertida a mensaje ROS 2
    target_pose.orientation = tf2::toMsg(q);

    // Asignar posición
    target_pose.position.x = x;
    target_pose.position.y = y;
    target_pose.position.z = z;

    return target_pose;
}

void exit_sig_handler(int signum)
{
    fprintf(stderr, "[emer_planner] Ctrl-C caught, exit process...\n");
    exit(-1);
}

class ShapeListener : public rclcpp::Node {
public:
    ShapeListener()
    : Node("shape_listener")
    {
        // Suscripción a los comandos (String)
        this->sub_ = this->create_subscription<std_msgs::msg::String>(
            "/xarm/shape_command",
            rclcpp::QoS(10),
            std::bind(&ShapeListener::on_command, this, std::placeholders::_1)
        );

        // Publisher de estado
        this->status_pub_ = this->create_publisher<std_msgs::msg::String>(
            "/xarm/shape_status", rclcpp::QoS(10)
        );

        // Instanciamos el planner usando el constructor simple que sólo pide group_name.
        // Esto evita problemas al pasar `this` (punteros compartidos).
        this->planner_ = std::make_shared<xarm_planner::XArmPlanner>("xarm6");
    }

    ~ShapeListener() {
        // asegurar que el hilo termine antes de destruir el nodo
        {   
            // usamos lock_guard para evitar que otros hilos en proceso sigan modificando stop_requested_
            std::lock_guard<std::mutex> lk(worker_mutex_);
            this->stop_requested_.store(true);
        }
        if (this->worker_thread_.joinable()) this->worker_thread_.join(); // Destruimos el hilo
    }

private:
    // Callback de suscripción
    void on_command(const std_msgs::msg::String::SharedPtr msg) {
        std::string command = msg->data; // Obtenemos la data del mensaje

        if (command == "stop") {
            this->stop_requested_.store(true); // Guardamos valor de true en stop_requested_
            publish_status("Stop command received");
            if (this->planner_) this->planner_->stopRobot();  // cancela ejecución
            return;
        }

        // map command -> handler
        // this se pasa como captura porque es algo fijo. Opcional poner '()' porque no haya parámetros
        std::function<void()> handler; // Creamos una variable que puede apuntar a cualquier función void
        if (command == "circle") handler = [this]{ this->execute_circle(); }; // Asignamos una función lambda, capturando this
        else if (command == "square") handler = [this]{ this->execute_square(); }; // Asignamos una función lambda, capturando this
        else { publish_status("Unknown command: " + command); return; } // Comando no conocido

        // ignorar si ya hay un comando ejecutándose
        bool expected = false;
        // Hacemos el equivalente atómico de worker_running_ == expected ? true : false y asignamos true o false
        if (!this->worker_running_.compare_exchange_strong(expected, true)) {
            publish_status("Robot busy, ignore command");
            return;
        }

        this->stop_requested_.store(false); // Reseteamos stop_requested_ porque se realizará un nuevo comando
        this->publish_status("Starting: " + command); // Publicación de status

        // ejecutar en hilo
        this->worker_thread_ = std::thread([this, handler, command]() { // Definimos el nuevo thread como un lambda
            bool success = false;
            try {
                handler(); // Ejecutamos la función que tenga handler
                success = true;
            } catch (...) { /* log, que en este caso no tenemos */ }

            if (this->stop_requested_.load()) this->publish_status(command + " cancelled by STOP");
            else if (success) this->publish_status(command + " completed");
            else this->publish_status(command + " failed");

            this->worker_running_.store(false); // Indicamos que ya no está corriendo el hilo
        });
        // El main no espera a que termine el thread como si usáramos join, se vuelve independiente
        this->worker_thread_.detach(); 
    }


    void publish_status(const std::string &text) {
        std_msgs::msg::String msg;
        msg.data = text;
        this->status_pub_->publish(msg);
        // Mostramos mensajes tipo DEBUG, INFO, WARN, ERROR o FATAL. "%s" indica string. c_str porque se espera const char*
        RCLCPP_INFO(this->get_logger(), "%s", text.c_str());
    }

    void execute_circle() {
        // Generar waypoints tipo círculo
        std::vector<geometry_msgs::msg::Pose> waypoints;
        double radius = 0.08;
        int resolution = 24;
        double center_x = 0.4, center_y = 0.0, z = 0.25;
        for (int i = 0; i < resolution; ++i) {
            double angle = 2.0 * M_PI * i / resolution;
            waypoints.push_back(create_target_pose(
                center_x + radius * std::cos(angle),
                center_y + radius * std::sin(angle),
                z, M_PI, 0.0, 0.0
            ));
        }
        waypoints.push_back(waypoints[0]); // cerrar el círculo
        this->execute_waypoints(waypoints);
    }

    void execute_square() {
        std::vector<geometry_msgs::msg::Pose> waypoints;
        double half = 0.06;
        double center_x = 0.4, center_y = 0.0, z = 0.25;
        std::vector<std::pair<double,double>> corners = {
            {center_x - half, center_y - half},
            {center_x + half, center_y - half},
            {center_x + half, center_y + half},
            {center_x - half, center_y + half}
        };
        for (const auto &c : corners) {
            waypoints.push_back(create_target_pose(c.first, c.second, z, M_PI, 0.0, 0.0));
        }
        waypoints.push_back(waypoints[0]);
        this->execute_waypoints(waypoints);
    }

    void execute_waypoints(const std::vector<geometry_msgs::msg::Pose> &waypoints) {
        for (const auto &pose : waypoints) {
            if (this->stop_requested_.load()) break;

            if (!this->planner_->planPoseTarget(pose)) {
                RCLCPP_ERROR(this->get_logger(), "Planificación fallida para una pose del camino");
                break;
            }

            if (this->stop_requested_.load()) break; // revisión adicional
            this->planner_->executePath();

            if (this->stop_requested_.load()) break; // revisión después de ejecutar
        }
        stop_requested_.store(false);
    }

    std::shared_ptr<xarm_planner::XArmPlanner> planner_; // Planner principal que define el pose targey y ejecuta el path
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr sub_; // Creamos un suscriptor para el nodo
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_pub_; // Creamos un publicador para el nodo

    // atomic bool en lugar de solo bool para acceso seguro desde múltiples hilos
    std::atomic<bool> worker_running_{false}; // Indica si el hilo principal sigue corriendo
    std::atomic<bool> stop_requested_{false}; // Indica si se solicitó detenerse

    std::thread worker_thread_;      // Hilo principal para ejecutar comandos
    std::mutex worker_mutex_;        // Mutual exclusion para proteger variables de ser modificadas por otros hilos
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<ShapeListener>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
