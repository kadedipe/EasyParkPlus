# Vehicle Seed Data Documentation

## Overview
This seed file populates the `user_vehicles` table with realistic vehicle data for testing and development.

## Data Categories

### Standard Sedans
- Tesla Model 3 (Electric)
- Toyota Camry
- Mercedes-Benz S-Class (Luxury)
- Porsche Taycan (Electric Luxury)

### SUVs
- Honda CR-V
- BMW X5 (Luxury)
- Ford Escape
- Hyundai IONIQ 5 (Electric)
- Ford Mustang Mach-E GT (Electric)
- Honda Pilot

### Trucks
- Ford F-150 Lariat

### Motorcycles
- Harley-Davidson Street Glide

## Vehicle Attributes

### Basic Information
- Plate numbers (unique identifiers)
- VIN (generated using custom function)
- Make and model
- Year (2020-2024)
- Color
- Vehicle type

### Electric Vehicle Data
- Battery capacity (kWh)
- Charging type (Level 2, DC Fast, Tesla Supercharger)
- Range estimates
- Charging preferences

### Physical Dimensions
- Length (feet)
- Width (feet)
- Height (feet)
- Weight (pounds)

### Ownership Information
- Default vehicle flag
- Creation and update timestamps
- User associations

## Usage Examples

### Querying Vehicles by User
```sql
SELECT uv.*, u.email 
FROM user_vehicles uv
JOIN users u ON uv.user_id = u.id
WHERE u.email = 'john.doe@example.com';