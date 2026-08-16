import Foundation
import Testing
@testable import Seasonly

struct SeasonlyTests {

    @Test func recommendationFeedDecodesServerSlateAndRankingMetadata() throws {
        let payload = """
        {
          "slate_id": "00000000-0000-0000-0000-000000000001",
          "country_code": "GB",
          "month": 7,
          "ranking_strategy": "seasonal_tfidf_v1",
          "personalized": true,
          "total": 1,
          "items": [
            {
              "id": "00000000-0000-0000-0000-000000000002",
              "name": "Seasonal pasta",
              "category": "Main",
              "area": "Italian",
              "country_of_origin": "Italy",
              "thumbnail_url": null,
              "instructions": "Cook it.",
              "matched_seasonal_produce": ["tomato"],
              "matched_seasonal_produce_count": 1
            }
          ]
        }
        """

        let feed = try JSONDecoder().decode(
            RecommendationFeed.self,
            from: Data(payload.utf8)
        )

        #expect(feed.slateId == UUID(uuidString: "00000000-0000-0000-0000-000000000001"))
        #expect(feed.rankingStrategy == "seasonal_tfidf_v1")
        #expect(feed.personalized)
        #expect(feed.items.map(\.name) == ["Seasonal pasta"])
    }

    @Test func privacyRequestsUseBackendSecurityContract() throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]

        let exportPayload = try encoder.encode(
            CurrentPasswordRequest(currentPassword: "correct-password")
        )
        let deletePayload = try encoder.encode(
            AccountDeletionRequest(
                currentPassword: "correct-password",
                confirmation: "DELETE"
            )
        )

        #expect(
            String(decoding: exportPayload, as: UTF8.self)
                == #"{"current_password":"correct-password"}"#
        )
        #expect(
            String(decoding: deletePayload, as: UTF8.self)
                == #"{"confirmation":"DELETE","current_password":"correct-password"}"#
        )
    }

}
