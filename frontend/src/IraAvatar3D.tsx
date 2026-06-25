import { useEffect, useRef } from "react";
import * as THREE from "three";

function glowMaterial(color: THREE.Color, opacity: number) {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
}

function lineMaterial(color: THREE.Color, opacity: number) {
  return new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
}

function makeCircle(radius: number, material: THREE.LineBasicMaterial, segments = 120) {
  const points: THREE.Vector3[] = [];

  for (let index = 0; index <= segments; index += 1) {
    const angle = (Math.PI * 2 * index) / segments;
    points.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0));
  }

  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
}

type IraAvatar3DProps = {
  gestureEnabled?: boolean;
  gestureSource?: HTMLVideoElement | null;
  isListening?: boolean;
  isSpeaking?: boolean;
  status?: string;
};

export function IraAvatar3D({
  gestureEnabled = false,
  gestureSource = null,
  isListening = false,
  isSpeaking = false,
  status = ""
}: IraAvatar3DProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const mount = mountRef.current;

    if (!mount) {
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, mount.clientWidth / mount.clientHeight, 0.1, 100);
    camera.position.set(0, 0, 8);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.dataset.testid = "ira-avatar-canvas";
    mount.appendChild(renderer.domElement);

    const hologram = new THREE.Group();
    scene.add(hologram);

    // --- State Colors Definition ---
    const COLOR_STANDBY = new THREE.Color(0x00f3ff);   // Electric Cyber Cyan
    const COLOR_LISTENING = new THREE.Color(0x00ffbb);  // Vivid Neon Green/Teal
    const COLOR_SPEAKING = new THREE.Color(0xd600ff);   // Deep Pulsing Purple/Magenta
    const COLOR_ERROR = new THREE.Color(0xff3366);      // Warning Sunset Red
    const COLOR_ASLEEP = new THREE.Color(0x3e307c);     // Dim Sleep Violet/Slate
    const COLOR_SUCCESS = new THREE.Color(0x00ff88);    // Face ID Approved Emerald

    const activeColor = COLOR_STANDBY.clone();

    // --- 1. Dynamic 3D Neural Wireframe Core ---
    const coreGeometry = new THREE.IcosahedronGeometry(1.25, 3);
    const positionAttribute = coreGeometry.attributes.position;
    const originalPositions = positionAttribute.array.slice() as Float32Array;

    const coreMaterial = new THREE.MeshBasicMaterial({
      color: activeColor,
      wireframe: true,
      transparent: true,
      opacity: 0.38,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
    hologram.add(coreMesh);

    // --- 2. Inner Glowing Energy Orb ---
    const innerGlowGeometry = new THREE.SphereGeometry(0.72, 32, 32);
    const innerGlowMaterial = glowMaterial(activeColor, 0.22);
    const innerGlowMesh = new THREE.Mesh(innerGlowGeometry, innerGlowMaterial);
    hologram.add(innerGlowMesh);

    // --- 3. Gyroscopic Holographic Rings ---
    const rings = new THREE.Group();
    hologram.add(rings);

    const ringSpecs = [
      [1.15, 0.44],
      [1.32, 0.36],
      [1.50, 0.28],
      [1.68, 0.22],
      [1.85, 0.16]
    ] as const;

    const ringMaterials: THREE.MeshBasicMaterial[] = [];
    ringSpecs.forEach(([radius, opacity]) => {
      const mat = glowMaterial(activeColor, opacity);
      ringMaterials.push(mat);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, 0.009, 8, 120), mat);
      rings.add(ring);
    });

    // --- 4. Cosmic Particle Orbit Cloud (3D Spherical Distribution) ---
    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions: number[] = [];

    for (let index = 0; index < 180; index += 1) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      const radius = 0.8 + Math.random() * 2.4;

      const px = radius * Math.sin(phi) * Math.cos(theta);
      const py = radius * Math.sin(phi) * Math.sin(theta);
      const pz = radius * Math.cos(phi);

      particlePositions.push(px, py, pz);
    }

    particleGeometry.setAttribute("position", new THREE.Float32BufferAttribute(particlePositions, 3));
    
    const particlesMaterial = new THREE.PointsMaterial({
      color: activeColor,
      transparent: true,
      opacity: 0.55,
      size: 0.022,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    
    const particles = new THREE.Points(particleGeometry, particlesMaterial);
    hologram.add(particles);

    // --- 5. Orbit Line Structures ---
    const orbitLines = new THREE.Group();
    hologram.add(orbitLines);

    const orbitMaterials: THREE.LineBasicMaterial[] = [];
    for (let index = 0; index < 6; index += 1) {
      const mat = lineMaterial(activeColor, 0.2 + index * 0.05);
      orbitMaterials.push(mat);
      const circle = makeCircle(1.48 + index * 0.05, mat);
      circle.scale.y = 0.68 + Math.sin(index) * 0.08;
      circle.rotation.z = index * 0.45;
      circle.rotation.x = Math.sin(index * 1.2) * 0.38;
      circle.rotation.y = Math.cos(index * 0.8) * 0.25;
      orbitLines.add(circle);
    }

    // --- Ambient Lights ---
    const light = new THREE.PointLight(0x86faff, 2.5, 8);
    light.position.set(0, 0, 3);
    scene.add(light, new THREE.AmbientLight(0x786cff, 0.4));

    const clock = new THREE.Clock();
    let frameId = 0;

    const animate = () => {
      const elapsed = clock.getElapsedTime();
      const statusUpper = (status || "").toUpperCase();

      // --- Determine State Colors ---
      let targetColor = COLOR_STANDBY;
      
      if (
        statusUpper.includes("ERROR") || 
        statusUpper.includes("CHECK") || 
        statusUpper.includes("ALLOW") || 
        statusUpper.includes("BLOCKED") ||
        statusUpper.includes("BUSY")
      ) {
        targetColor = COLOR_ERROR;
      } else if (statusUpper.includes("ACCESS CONFIRMED") || statusUpper.includes("RECOGNIZED")) {
        targetColor = COLOR_SUCCESS;
      } else if (statusUpper.includes("ASLEEP") || statusUpper.includes("STARTING") || statusUpper.includes("OFFLINE")) {
        targetColor = COLOR_ASLEEP;
      } else if (isSpeaking) {
        targetColor = COLOR_SPEAKING;
      } else if (isListening) {
        targetColor = COLOR_LISTENING;
      }

      // Smoothly interpolate colors (lerp)
      activeColor.lerp(targetColor, 0.08);

      // Apply lerped color to all visual nodes
      coreMaterial.color.copy(activeColor);
      innerGlowMaterial.color.copy(activeColor);
      particlesMaterial.color.copy(activeColor);
      ringMaterials.forEach(m => m.color.copy(activeColor));
      orbitMaterials.forEach(m => m.color.copy(activeColor));

      // --- Custom Neural Core 3D Wave Deformation ---
      let waveSpeed = 1.8;
      let waveAmplitude = 0.06;

      if (statusUpper.includes("ASLEEP") || statusUpper.includes("OFFLINE")) {
        waveSpeed = 0.6;
        waveAmplitude = 0.02;
      } else if (isSpeaking) {
        waveSpeed = 5.2;
        waveAmplitude = 0.26;
      } else if (isListening) {
        waveSpeed = 3.6;
        waveAmplitude = 0.18;
      } else if (gestureEnabled) {
        waveSpeed = 2.6;
        waveAmplitude = 0.14;
      }

      const timeScale = elapsed * waveSpeed;
      const tempPos = new THREE.Vector3();
      const direction = new THREE.Vector3();

      for (let i = 0; i < positionAttribute.count; i++) {
        const ox = originalPositions[i * 3];
        const oy = originalPositions[i * 3 + 1];
        const oz = originalPositions[i * 3 + 2];

        tempPos.set(ox, oy, oz);
        direction.copy(tempPos).normalize();

        // 3D Wave Simulation using sines and cosines
        const displacement =
          Math.sin(ox * 2.8 + timeScale) * waveAmplitude +
          Math.cos(oy * 3.4 + timeScale * 1.2) * (waveAmplitude * 0.8) +
          Math.sin(oz * 2.2 + timeScale * 0.8) * (waveAmplitude * 0.5);

        // Apply displacement outwards along vertex normals
        const finalRadius = 1.15 + displacement;
        const displaced = direction.multiplyScalar(finalRadius);

        positionAttribute.setXYZ(i, displaced.x, displaced.y, displaced.z);
      }
      positionAttribute.needsUpdate = true;

      // --- Gyroscopic 3D Rotations ---
      const gesturePulse = gestureEnabled && gestureSource?.readyState ? 0.04 : 0;
      
      hologram.rotation.z = Math.sin(elapsed * 0.12) * 0.04 + Math.sin(elapsed * 2.0) * gesturePulse;
      hologram.scale.setScalar(1 + Math.sin(elapsed * 1.4) * (0.015 + gesturePulse * 0.4));

      // Multi-axis rotations for the surrounding gyroscopic rings
      rings.children.forEach((ring, idx) => {
        const dir = idx % 2 === 0 ? 1 : -1;
        ring.rotation.x = elapsed * 0.06 * (idx + 1) * dir;
        ring.rotation.y = elapsed * 0.04 * (idx + 1) * dir;
        ring.rotation.z = elapsed * 0.1 * dir;
      });

      // Slowly rotate particle cloud and orbit frames
      particles.rotation.y = -elapsed * 0.03;
      particles.rotation.z = -elapsed * 0.01;
      orbitLines.rotation.z = -elapsed * 0.08;

      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    };

    const handleResize = () => {
      const { clientWidth, clientHeight } = mount;
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(clientWidth, clientHeight);
    };

    window.addEventListener("resize", handleResize);
    animate();

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", handleResize);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
    };
  }, [gestureEnabled, gestureSource, isListening, isSpeaking, status]);

  return <div ref={mountRef} className="avatar-3d" aria-label="IRA hologram circle" />;
}
