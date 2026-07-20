// parking-management/backend/src/scripts/optimize-indexes.js
import { dbManager } from '../config/database.js';

class IndexOptimizer {
  constructor() {
    this.queries = [];
  }

  /**
   * Analyze slow queries and recommend indexes
   */
  async analyzeSlowQueries() {
    console.log('🔍 Analyzing slow queries...');
    
    // Check for tables without indexes
    const tables = await dbManager.primaryClient.$queryRaw`
      SELECT 
        table_name,
        (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
      FROM information_schema.tables t
      WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    `;

    for (const table of tables) {
      const indexes = await dbManager.primaryClient.$queryRaw`
        SELECT 
          indexname,
          indexdef
        FROM pg_indexes
        WHERE tablename = ${table.table_name}
      `;

      if (indexes.length === 0) {
        console.log(`  ⚠️ Table ${table.table_name} has no indexes`);
        this.queries.push({
          type: 'recommendation',
          table: table.table_name,
          message: 'Create indexes for frequently queried columns',
        });
      }
    }

    return this.queries;
  }

  /**
   * Generate index creation statements
   */
  generateIndexes() {
    const indexes = {
      users: [
        'CREATE INDEX idx_users_email ON users(email)',
        'CREATE INDEX idx_users_role ON users(role)',
        'CREATE INDEX idx_users_created_at ON users(created_at)',
      ],
      parking_spots: [
        'CREATE INDEX idx_parking_spots_status ON parking_spots(status)',
        'CREATE INDEX idx_parking_spots_city ON parking_spots(city)',
        'CREATE INDEX idx_parking_spots_lat_lng ON parking_spots(latitude, longitude)',
        'CREATE INDEX idx_parking_spots_rating ON parking_spots(rating)',
        'CREATE INDEX idx_parking_spots_hourly_rate ON parking_spots(hourly_rate)',
        'CREATE INDEX idx_parking_spots_features ON parking_spots USING gin(features)',
      ],
      bookings: [
        'CREATE INDEX idx_bookings_user_id ON bookings(user_id)',
        'CREATE INDEX idx_bookings_parking_id ON bookings(parking_id)',
        'CREATE INDEX idx_bookings_status ON bookings(status)',
        'CREATE INDEX idx_bookings_start_time ON bookings(start_time)',
        'CREATE INDEX idx_bookings_end_time ON bookings(end_time)',
        'CREATE INDEX idx_bookings_user_status ON bookings(user_id, status)',
        'CREATE INDEX idx_bookings_parking_status ON bookings(parking_id, status)',
      ],
      payments: [
        'CREATE INDEX idx_payments_booking_id ON payments(booking_id)',
        'CREATE INDEX idx_payments_status ON payments(status)',
        'CREATE INDEX idx_payments_created_at ON payments(created_at)',
        'CREATE INDEX idx_payments_booking_status ON payments(booking_id, status)',
      ],
      reviews: [
        'CREATE INDEX idx_reviews_parking_id ON reviews(parking_id)',
        'CREATE INDEX idx_reviews_user_id ON reviews(user_id)',
        'CREATE INDEX idx_reviews_rating ON reviews(rating)',
        'CREATE INDEX idx_reviews_parking_rating ON reviews(parking_id, rating)',
      ],
      availability: [
        'CREATE INDEX idx_availability_parking_id ON availability(parking_id)',
        'CREATE INDEX idx_availability_date ON availability(date)',
        'CREATE INDEX idx_availability_parking_date ON availability(parking_id, date)',
      ],
      notifications: [
        'CREATE INDEX idx_notifications_user_id ON notifications(user_id)',
        'CREATE INDEX idx_notifications_read ON notifications(read)',
        'CREATE INDEX idx_notifications_created_at ON notifications(created_at)',
        'CREATE INDEX idx_notifications_user_read ON notifications(user_id, read)',
      ],
    };

    return indexes;
  }

  /**
   * Apply recommended indexes
   */
  async applyIndexes() {
    console.log('📊 Applying recommended indexes...');
    
    const indexStatements = this.generateIndexes();
    let applied = 0;
    let errors = 0;

    for (const [table, statements] of Object.entries(indexStatements)) {
      console.log(`  Table: ${table}`);
      
      for (const statement of statements) {
        try {
          await dbManager.primaryClient.$executeRawUnsafe(statement);
          applied++;
          console.log(`    ✓ ${statement}`);
        } catch (error) {
          if (error.message.includes('already exists')) {
            console.log(`    ○ ${statement} (already exists)`);
          } else {
            console.log(`    ✗ ${statement} (${error.message})`);
            errors++;
          }
        }
      }
    }

    console.log(`\n✅ Applied ${applied} indexes, ${errors} errors`);
    
    return { applied, errors };
  }
}

const optimizer = new IndexOptimizer();
optimizer.applyIndexes().catch(console.error);