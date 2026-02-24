// esp32-oled-18650 (c) by Normen Hansen
// v1.0 - initial release
// released under MIT License
// uses the BOSL Library (https://github.com/revarbat/BOSL)
include <BOSL/constants.scad>
use <BOSL/shapes.scad>

use <ttgo18650esp32.scad>

/** VARIABLES **/
// show the lid?
displayLid = true;
// show the case?
displayCase = true;
// show the PCB?
displayPCB = false;
// place the lid on the ground?
laydownLid = true;
// extension for the lid, increase to get more space above the PCB pins
lidextension = 2;
// x-axis inset for lid, increase if lid is too tight, reduce if its too loose
inset = 0.3;
// y-axis inset for lid, increase if lid is bending upwards, reduce if its too loose
insety = 0.6;
inset2 = 2 * inset;
insety2 = 2 * insety;
// height of the casing, increase if display doesn't fit
height = 26;
// width of the casing, should be okay
width = 34;
// length of the casing, should be okay
length = 120;
// wall thickness, 2mm keeps it stable
walls = 2;
// space for pcb (between lockdowns)
pcbspace = 2;
// pcb level (from z=0)
dheight = 20;
// pcb distancers distance to corner
ddist = 4.2;
// length of the display part
displength = 40;
// x position of screen
screenx = 5;
// y position of screen
screeny = 31;
// width of screen
screenw = 24;
// height of screen
screenh = 12;
// y position of buttons
buttony = 35;
// x position of enable button
buttonenx = 4;
// x position of boot button
buttonbootx = 28.5;
// radius of button
buttond = 1;
// lid groove height
grheight = 2;
// lid groove width
grwidth = .8;
// clamp down pegs
pegsize = (ddist - walls) * 2;
// top side clip-in width
clipwidth = 10;
clipdepth = walls + grwidth + 2;
// top side clip-in height
clipheight = 2;
// additional insets for clip hole (clip is inset too)
clipinset = 0.3;
clipinset2 = 2 * clipinset;
// PCB holder bar
boff = length - displength; // y offset
// PCB holder bar width
bwidth = 2;
// PCB holder bar height
bheight = 5;
blength = length - boff - walls;

// code to display
if (displayLid) {
  if (laydownLid) {
    translate([- 10, 0, height + lidextension]) rotate([0, 180, 0])
      lid(lidextension);
  } else {
    lid(lidextension);
  }
}
if (displayCase) {
  case();
}
if (displayPCB) {
  color("blue") translate([2.5, 2.5, 20]) ttgo18650esp32();
}

// the lid
module lid(extheight = walls) {
  // extension height (above board, not display part)
  // lid
  difference() {
    union() {
      // display part
      translate([0, length - displength, height])
        roundedCube(dimensions = [width, displength, walls]);
      // PCB pin box part
      difference() {
        translate([0, 0, height])
          roundedCube(dimensions = [width, length - (displength - walls), extheight]);
        translate([0 + walls + grwidth + inset, 0 + walls + grwidth + insety, height - 0.1])
          roundedCube(dimensions = [width - (walls * 2) - (grwidth * 2) - inset2, length - displength - (walls * 2) -
            insety - grwidth, extheight + 0.1 - walls]);
      }
      // groove (inset offset)
      difference() {
        translate([walls + inset, walls + insety, height - grheight])
          roundedCube(dimensions = [width - (walls * 2) - inset2, length - (walls * 2) - insety2, grheight]);
        translate([walls + grwidth + inset, walls + grwidth + insety, height - grheight - 0.1])
          roundedCube(dimensions = [width - (walls * 2) - (grwidth * 2) - inset2, length - (walls * 2) - (grwidth * 2) -
            insety2, (grheight) + 0.2]);
        cutouts();
      }
      // pcb clamp pegs
      translate([walls + inset, walls + insety, dheight + pcbspace])
        roundedCube(dimensions = [pegsize - inset2, pegsize - insety2, height + extheight - dheight - pcbspace]);
      translate([width - walls - pegsize + inset, walls + insety, dheight + pcbspace])
        roundedCube(dimensions = [pegsize - inset2, pegsize - insety2, height + extheight - dheight - pcbspace]);
      translate([walls + inset, length - walls - pegsize + insety, dheight + pcbspace])
        roundedCube(dimensions = [pegsize - inset2, pegsize - insety2, height - dheight - pcbspace]);
      translate([width - walls - pegsize + inset, length - walls - pegsize + insety, dheight + pcbspace])
        roundedCube(dimensions = [pegsize - inset2, pegsize - insety2, height - dheight - pcbspace]);
      // lid clip-in
      translate([(width / 2) - (clipwidth / 2), length - clipdepth, dheight + pcbspace]) lidClip();
    }
    // display
    translate([screenx, length - screeny, height - 0.1])
      cube([screenw, screenh, 10]);
    // EN button
    translate([buttonenx, length - buttony, height - 0.1])
      cylinder(walls + 0.2, buttond, $fn = 32);
    // Boot button
    translate([buttonbootx, length - buttony, height - 0.1])
      cylinder(walls + 0.2, buttond, $fn = 32);
    // pcb screw holes
    translate([ddist, ddist, dheight + pcbspace - 0.1])
      cylinder(height + extheight, 1, $fn = 32);
    translate([width - ddist, ddist, dheight + pcbspace - 0.1])
      cylinder(height + extheight, 1, $fn = 32);
    /*translate([ddist,length-ddist,dheight+pcbspace]) cylinder(height,1,$fn=32);
    translate([width-ddist,length-ddist,dheight+pcbspace]) cylinder(height,1,$fn=32);*/
  }
}

// the case (box)
module case() {
  // box
  difference() {
    union() {
      enclosure(width, length, height, walls);
      distancer(ddist, ddist, 0, dheight);
      distancer(width - ddist, ddist, 0, dheight);
      /*distancer(ddist,length - ddist,0,dheight);
      distancer(width - ddist, length - ddist,0,dheight);*/
      // PCB rails
      translate([walls, boff, dheight]) rotate([0, 90, 0])
        right_triangle([bheight, blength, bwidth], ORIENT_Y);
      translate([width - walls, boff + blength, dheight]) rotate([0, 90, 180])
        right_triangle([bheight, blength, bwidth], ORIENT_Y);
    }
    cutouts();
    // lid clip-in (slightly larger)
    translate([(width / 2) - (clipwidth / 2) - clipinset, length - clipdepth - clipinset, dheight + pcbspace - clipinset
      ])
      cube([clipwidth + clipinset2, clipdepth + clipinset2, clipheight + clipinset2]);
  }
}

// lid clip
module lidClip() {
  rotate([90, 0, 90])
    linear_extrude(clipwidth)
      polygon([[0, 0],
          [clipdepth - walls, 0],
          [clipdepth, clipheight / 2],
          [clipdepth - walls - insety, clipheight],
          [clipdepth - walls - insety, clipheight + (height - dheight - pcbspace - walls)],
          [0, clipheight + (height - dheight - pcbspace - walls)],
          [0, clipheight]]);
}

// the plug/switch cutouts
module cutouts() {
  translate([- 1, 7, dheight - 1])
    cube([8, 12, 8]);
  translate([width - 7, 8.5, dheight + 1.5])
    cube([8, 10.2, 4.6]);
}

// makes the base bottom enclosure
module enclosure(xSize = 25, ySize = 90, zSize = 25, walls = 2) {
  difference() {
    roundedCube(dimensions = [xSize, ySize, zSize]);
    translate([walls, walls, walls])
      roundedCube(dimensions = [xSize - (walls * 2), ySize - (walls * 2), zSize - (walls * 1) + 0.5]);
  }
}

// places a distancer with a hole
module distancer(posX = 0, posY = 0, posZ = 0, height = 5, baseRadius = 2.5, topRadius = 2.5, holeRadius = 1) {
  translate([posX, posY, posZ]) difference() {
    cylinder(r1 = baseRadius, r2 = topRadius, h = height, $fn = 32);
    cylinder(r = holeRadius, h = height + 0.5, $fn = 32);
  }
}

// rounded cube from aurduino case library
module roundedCube(dimensions = [10, 10, 10], cornerRadius = 1, faces = 32) {
  hull() cornerCylinders(dimensions = dimensions, cornerRadius = cornerRadius, faces = faces);
}

module cornerCylinders(dimensions = [10, 10, 10], cornerRadius = 1, faces = 32) {
  translate([cornerRadius, cornerRadius, 0]) {
    cylinder(r = cornerRadius, $fn = faces, h = dimensions[2]);
    translate([dimensions[0] - cornerRadius * 2, 0, 0]) cylinder(r = cornerRadius, $fn = faces, h = dimensions[2]);
    translate([0, dimensions[1] - cornerRadius * 2, 0]) {
      cylinder(r = cornerRadius, $fn = faces, h = dimensions[2]);
      translate([dimensions[0] - cornerRadius * 2, 0, 0]) cylinder(r = cornerRadius, $fn = faces, h = dimensions[2]);
    }
  }
}
