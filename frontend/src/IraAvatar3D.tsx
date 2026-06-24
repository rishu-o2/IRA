import { useEffect, useRef } from "react";
import * as THREE from "three";

function glowMaterial(color: number, opacity: number) {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
}

function lineMaterial(color: number, opacity: number) {
  return new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
}

function makeCircle(radius: number, material: THREE.LineBasicMaterial, segments = 192) {
  const points: THREE.Vector3[] = [];

  for (let index = 0; index <= segments; index += 1) {
    const angle = (Math.PI * 2 * index) / segments;
    points.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0));
  }

  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
}

function makeIraTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 256;
  const context = canvas.getContext("2d");

  if (context) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.font = "300 104px Segoe UI, Arial, sans-serif";
    context.fillStyle = "rgba(239, 253, 255, 0.9)";
    context.shadowColor = "rgba(89, 238, 255, 0.95)";
    context.shadowBlur = 24;
    context.fillText("I  R  A", 340, 158);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

type IraAvatar3DProps = {
  gestureEnabled?: boolean;
  gestureSource?: HTMLVideoElement | null;
};

export function IraAvatar3D({ gestureEnabled = false, gestureSource = null }: IraAvatar3DProps) {
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

    const core = new THREE.Mesh(new THREE.CircleGeometry(1.42, 160), glowMaterial(0x351a7a, 0.16));
    hologram.add(core);

    const rings = new THREE.Group();
    hologram.add(rings);

    const ringSpecs = [
      [1.1, 0x50f8ff, 0.72, 0],
      [1.27, 0xb16cff, 0.58, 0.55],
      [1.45, 0x50f8ff, 0.44, -0.35],
      [1.63, 0xb16cff, 0.36, 0.88],
      [1.82, 0x5d8dff, 0.28, -0.72]
    ] as const;

    ringSpecs.forEach(([radius, color, opacity, rotation]) => {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, 0.01, 8, 220), glowMaterial(color, opacity));
      ring.rotation.z = rotation;
      rings.add(ring);
    });

    const orbitLines = new THREE.Group();
    hologram.add(orbitLines);

    for (let index = 0; index < 8; index += 1) {
      const circle = makeCircle(1.46 + index * 0.035, lineMaterial(index % 2 ? 0xb16cff : 0x50f8ff, 0.28 + index * 0.035));
      circle.scale.y = 0.74 + Math.sin(index) * 0.08;
      circle.rotation.z = index * 0.38;
      circle.rotation.x = Math.sin(index * 1.4) * 0.42;
      circle.rotation.y = Math.cos(index * 0.9) * 0.28;
      orbitLines.add(circle);
    }

    const texture = makeIraTexture();
    const label = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: 0.82,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    label.scale.set(2.75, 0.68, 1);
    label.position.z = 0.16;
    hologram.add(label);

    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions: number[] = [];

    for (let index = 0; index < 90; index += 1) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 0.35 + Math.random() * 1.75;
      particlePositions.push(Math.cos(angle) * radius, Math.sin(angle) * radius, (Math.random() - 0.5) * 0.6);
    }

    particleGeometry.setAttribute("position", new THREE.Float32BufferAttribute(particlePositions, 3));
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({
        color: 0x9ffaff,
        transparent: true,
        opacity: 0.42,
        size: 0.024,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    hologram.add(particles);

    const light = new THREE.PointLight(0x86faff, 3, 8);
    light.position.set(0, 0, 3);
    scene.add(light, new THREE.AmbientLight(0x786cff, 0.7));

    const clock = new THREE.Clock();
    let frameId = 0;

    const animate = () => {
      const elapsed = clock.getElapsedTime();
      const gesturePulse = gestureEnabled && gestureSource?.readyState ? 0.035 : 0;
      hologram.rotation.z = Math.sin(elapsed * 0.16) * 0.035 + Math.sin(elapsed * 1.8) * gesturePulse;
      hologram.scale.setScalar(1 + Math.sin(elapsed * 1.3) * (0.018 + gesturePulse * 0.35));
      rings.rotation.z = elapsed * 0.13;
      orbitLines.rotation.z = -elapsed * 0.1;
      particles.rotation.z = -elapsed * 0.04;
      label.material.opacity = 0.68 + Math.sin(elapsed * 2.6) * 0.14;
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
      texture.dispose();
      renderer.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
    };
  }, [gestureEnabled, gestureSource]);

  return <div ref={mountRef} className="avatar-3d" aria-label="IRA hologram circle" />;
}
