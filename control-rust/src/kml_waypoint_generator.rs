use std::old_io::BufferedReader;
use std::old_io::File;
use std::old_io::fs::PathExtensions;
use std::old_io::process::Command;

use waypoint_generator::WaypointGenerator;


/**
 * Loads and returns waypoints from a KML file.
 */
#[allow(dead_code)]
struct KmlWaypointGenerator {
    waypoints: Vec<(f32, f32)>,
    current_waypoint: u32,
}


impl KmlWaypointGenerator {
    #[allow(dead_code)]
    pub fn new(file_name: &str) -> KmlWaypointGenerator {
        KmlWaypointGenerator {
            waypoints: KmlWaypointGenerator::load_waypoints(file_name),
            current_waypoint: 0
        }
    }
    fn load_waypoints(file_name: &str) -> Vec<(f32, f32)> {
        let path = Path::new(file_name);
        if !path.exists() || !path.is_file() {
            panic!("File does not exist: {}", file_name);
        }

        // A KML file is a zip archive containing a single file named "doc.kml"
        // that is an XML file
        let temp_directory = "/tmp/waypoints";
        let zip_io_result = Command::new("unzip")
            .arg(file_name)
            .arg("-d")  // Output directory
            .arg(temp_directory)
            .spawn();
        match zip_io_result {
            Ok(_) => (),
            Err(e) => panic!("Failed to unzip file: {}", e),
        };

        let mut waypoints = Vec::<(f32, f32)>::new();
        let file_path = Path::new("/tmp/doc.kml");
        let mut xml_file = BufferedReader::new(File::open(&file_path));
        let mut coordinates_open_tag = false;
        // We should use a real XML parser here, but Google Earth saves the
        // <coordinates> tag on one line, then the coordinates on the next,
        // then the closing </coordinates> tag on the next, so we'll just rely
        // on that fact
        for line_option in xml_file.lines() {
            match line_option {
                Ok(line) => {
                    if line.as_slice().contains("<coordinates>") {
                        coordinates_open_tag = true;
                    } else if coordinates_open_tag {
                        let mut latitude = 0.0f32;
                        let mut longitude = 0.0f32;
                        for long_lat_alt in line.as_slice().words() {
                            let mut iterator = long_lat_alt.split(',');
                            let mut success = true;
                            match iterator.next() {
                                Some(longitude_str) => {
                                    let parsed_longitude = longitude_str.parse::<f32>();
                                    match parsed_longitude {
                                        Ok(longitude_) => longitude = longitude_,
                                        Err(e) => {
                                            println!("Unable to parse longitude: '{}', {}", longitude_str, e);
                                            success = false;
                                        },
                                    }
                                },
                                None => println!("No longitude"),
                            }

                            match iterator.next() {
                                Some(latitude_str) => {
                                    let parsed_latitude = latitude_str.parse::<f32>();
                                    match parsed_latitude {
                                        Ok(latitude_) => latitude = latitude_,
                                        Err(e) => {
                                            println!("Unable to parse latitude: '{}', {}", latitude_str, e);
                                            success = false;
                                        },
                                    }
                                }
                                None => println!("No latitude"),
                            }

                            if success {
                                waypoints.push((latitude, longitude));
                            }
                        }
                        break;
                    }
                }
                Err(e) => println!("error {}", e),
            }
        }
        waypoints
    }
}


impl WaypointGenerator for KmlWaypointGenerator {
    #[allow(unused_variables)]
    fn get_current_waypoint(&self, x_m: f32, y_m: f32) -> (f32, f32) {
        // TODO
        (0.0, 0.0)
    }

    #[allow(unused_variables)]
    fn get_current_raw_waypoint(&self, x_m: f32, y_m: f32) -> (f32, f32) {
        // TODO
        (0.0, 0.0)
    }

    fn next(&self) {
        // TODO
    }

    #[allow(unused_variables)]
    fn reached(&self, x_m: f32, y_m: f32) -> bool {
        // TODO
        return false;
    }

    fn done(&self) -> bool {
        // TODO
        return false;
    }
}
