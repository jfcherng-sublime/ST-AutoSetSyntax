% Example of a controller based on quadratic programming with Euclidean error calculation.
%
% CONSTRAINED_CONTROLLER_EXAMPLE(plane_constraint) Runs a simple example where a
% controller based on classic quadratic programming and the objective function
% min 0.5 * norm(J*u + gain*task_error)^2 + 0.5*lambda*norm(u)^2 is
% used with an Euclidean error to control the end-effector pose while it is
% constrained by a plane.
% If plane_constraint = 0, the trajectory is NOT constrained by the plane in the
% workspace, otherwise the trajectory is contrained by the plane.

% (C) Copyright 2011-2019 DQ Robotics Developers
%
% This file is part of DQ Robotics.
%
%     DQ Robotics is free software: you can redistribute it and/or modify
%     it under the terms of the GNU Lesser General Public License as published by
%     the Free Software Foundation, either version 3 of the License, or
%     (at your option) any later version.
%
%     DQ Robotics is distributed in the hope that it will be useful,
%     but WITHOUT ANY WARRANTY; without even the implied warranty of
%     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%     GNU Lesser General Public License for more details.
%
%     You should have received a copy of the GNU Lesser General Public License
%     along with DQ Robotics.  If not, see <http://www.gnu.org/licenses/>.
%
% DQ Robotics website: dqrobotics.github.io
%
% Contributors to this file:
%     Bruno Vihena Adorno - adorno@ufmg.br

function constrained_controller_example(use_constraint)
    if nargin == 0
        use_plane_constraint = 1;
    elseif use_constraint == 0
        use_plane_constraint = 0;
    else
        use_plane_constraint = 1;
    end


    % use the namespace
    include_namespace_dq

    % We use a KUKA LWR4 robot
    kuka = KukaLwr4Robot.kinematics();
    kuka.name = 'KUKA';
    
    % Initial configuration
    q = [pi/2, -1.8*pi/2, 0, -1.5*pi/2, -1.5*pi/2, 0, 0]';
    % Integration step
    T = 0.001;
    
    solver = DQ_QuadprogSolver;

    % The controller is given by
    % u = argmin 0.5 * norm(J*qdot + gain*task_error)^2 + 0.5*lambda*norm(qdot)^2,
    %      qdot
    % where J is the robot Jacobian, gain determines the convergence rate,
    % task_error is the error between the current task variable and
    % the desired one, and lambda is the damping factor. When the task error
    % derivative is below stability_threshold, the closed-loop system is
    % said to have reached a stable region.
    controller = DQ_ClassicQPController(kuka,solver);
    controller.set_gain(100);
    controller.set_stability_threshold(0.0001);

    % Prepare the visualization
    figure;
    view(143,20);
    axis equal;
    axis([-0.5, 0.5,-0.6, 0.6, -0.1, 0.6])
    hold on;

    % The task variable to be controlled is the end-effector pose
    controller.set_control_objective(ControlObjective.Pose);

    % Define the admissible region, which is the region from one side of
    % a plane
    p = -0.15*i_ -0.1*j_ + 0.18*k_;
    r = cos(pi/16) + i_*sin(pi/16);
    xplane = r + E_*(1/2)*p*r;

    plane = Adsharp(xplane,-k_);

    %%%%%%%%%%%% define reference for the controller %%%%%%%%%%%%%%%
    x_pose = 1 + E_*(1/2)*(-0.15*i_ -0.5*j_ + 0.1*k_);
    task_reference = vec8(x_pose);
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


    %%%%%%%%%%%%%%%%%%%% begin eye candy %%%%%%%%%%%%%%%%%%%%%%%%%
    title('Controlling the pose.');
    % plot the reference to aid in the visualization
    plot(x_pose, 'scale', 0.2, 'name', 'desired pose');
    
    % plot the plane constraint
    plot(plane, 'plane', 5, 'color', 'c');
    
    %plot the robot
    plot(kuka,q', 'nojoints');
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    pause(1);
    
    % This is actually the important part on how to use the controller.
    while ~controller.system_reached_stable_region()
        
        x_pose = kuka.fkm(q);
        p = translation(x_pose);  
        
        if use_plane_constraint ~= 0
            % First we define a differential inequality given by d_dot >= -eta*d, 
            % where d is the distance from the end-effector to the
            % plane, d_dot is its time derivative and eta determines the
            % maximum rate for the approach velocity.
            % To calculate the aforementioned differential inequality, we need
            % to calculate the point-to-plane distance Jacobian
        
            J_pose = kuka.pose_jacobian(q);                 
            J_trans = kuka.translation_jacobian(J_pose,x_pose);

            Jdist = kuka.point_to_plane_distance_jacobian(J_trans, p, plane);
            dist = DQ_Geometry.point_to_plane_distance(p,plane);
        
            % Add inequality constraint d_dot >= -eta*d, which implies    
            % -d_dot <= eta*d, where d_dot = Jdist*u; therefore 
            % -Jdist*u <= eta*d. Let's choose eta = 10.
            controller.set_inequality_constraint(-Jdist,100*dist);
        end
        
        % Let us calculate the control input
        u = controller.compute_setpoint_control_signal(q, task_reference);
        
        % Do a numerical integration to update the robot in Matlab. In
        % an actual robot actuated by means of velocity inputs, this step
        % is not necessary.
        q = q + T*u;

        % Draw the robot in Matlab.
        plot(kuka,q', 'nojoints');
        
        pvec = vec3(p);
        plot3(pvec(1),pvec(2),pvec(3), 'ro');
        drawnow;
        %pause;
    end
end



