```scad
// IKEA Markus Chair - OpenSCAD Model (Colorized)
// Note: Render with CGAL (F6) for final geometry. $fn is kept moderate for faster preview (F5).

$fn = 40;

module caster() {
    color("#1a1a1a") { // Black plastic
        // Caster base/hood
        translate([0, 0, 15]) cylinder(h=20, r=18, center=true);
        // Dual wheels
        translate([0, 0, 15]) {
            rotate([90, 0, 0]) {
                translate([0, 0, 12]) cylinder(h=10, r=25, center=true);
                translate([0, 0, -12]) cylinder(h=10, r=25, center=true);
                // Axle
                cylinder(h=30, r=4, center=true);
            }
        }
    }
}

module star_base() {
    // 5-point star base - Aluminum
    color("#c0c0c0") { 
        for(i = [0 : 4]) {
            rotate([0, 0, i * 360 / 5]) {
                hull() {
                    translate([0, 0, 40]) cylinder(h=30, r=35);
                    translate([320, 0, 20]) cylinder(h=15, r=20);
                }
            }
        }
        // Center column hub
        translate([0, 0, 40]) cylinder(h=60, r=38);
    }
    
    // Attach casters to the ends of the base
    for(i = [0 : 4]) {
        rotate([0, 0, i * 360 / 5]) {
            translate([320, 0, -10]) caster();
        }
    }
}

module gas_cylinder() {
    // Outer sleeve (Black plastic)
    color("#111111") 
        translate([0, 0, 100]) cylinder(h=140, r=25);
        
    // Inner pneumatic cylinder (Steel)
    color("#999999") 
        translate([0, 0, 240]) cylinder(h=130, r=14);
}

module mechanism() {
    color("#151515") { // Dark black/grey metal box
        // Under-seat tilt/lift mechanism box
        translate([0, -20, 385]) cube([180, 220, 40], center=true);
        // Tension knob
        translate([0, 100, 385]) rotate([90, 0, 0]) cylinder(h=30, r=25);
        // Lift lever
        translate([90, -40, 385]) rotate([0, 90, 0]) cylinder(h=80, r=5);
    }
}

module seat() {
    // Contoured seat pan cushion (Dark Grey Fabric)
    color("#2c2d2e") {
        translate([0, 20, 425]) {
            minkowski() {
                cube([490, 450, 40], center=true);
                sphere(r=15);
            }
        }
    }
}

module backrest() {
    translate([0, -210, 450]) {
        rotate([-8, 0, 0]) { 
            
            // Outer frame (Black plastic/metal)
            color("#151515") {
                difference() {
                    translate([0, 0, 390]) 
                        minkowski() {
                            cube([420, 20, 760], center=true);
                            cylinder(h=10, r=10, center=true);
                        }
                    translate([0, 0, 350]) 
                        cube([380, 50, 700], center=true);
                }
                
                // Lower attachment bracket connecting backrest to mechanism
                translate([0, 10, -30]) cube([150, 15, 60], center=true);
            }
            
            // Backrest Mesh (Dark grey/black mesh)
            color("#222222")
                translate([0, 5, 345]) cube([380, 2, 690], center=true);

            // Headrest Cushion (Dark Grey Fabric/Leather)
            color("#2c2d2e") {
                translate([0, 15, 740]) {
                    minkowski() {
                        cube([400, 35, 140], center=true);
                        sphere(r=12);
                    }
                }
            }

            // Lumbar Support Pad (Black)
            color("#111111") {
                translate([0, 20, 140]) {
                    rotate([10, 0, 0]) {
                        minkowski() {
                            cube([360, 25, 90], center=true);
                            sphere(r=10);
                        }
                    }
                }
            }
        }
    }
}

module armrests() {
    // Left and Right armrests
    for (m = [0, 1]) {
        mirror([m, 0, 0]) {
            translate([240, -50, 390]) {
                // Upright steel tube (Aluminum/Silver)
                color("#c0c0c0") 
                    cylinder(h=190, r=12);
                    
                // Horizontal support under pad (Aluminum/Silver)
                color("#c0c0c0")
                    translate([0, 50, 185]) cube([20, 250, 10], center=true);
                    
                // Armrest Pad (Black/Dark Grey rubberized plastic)
                color("#2c2d2e") {
                    translate([0, 50, 195]) {
                        minkowski() {
                            cube([35, 260, 10], center=true);
                            sphere(r=6);
                        }
                    }
                }
            }
        }
    }
}

module ikea_markus_chair() {
    star_base();
    gas_cylinder();
    mechanism();
    seat();
    backrest();
    armrests();
}

// Assemble the colored chair
ikea_markus_chair();
```