import Foundation
import Testing
@testable import Seasonly

struct SeasonlyTests {

    private func recipe(_ name: String, id: UUID = UUID()) -> SeasonalRecipe {
        SeasonalRecipe(
            id: id,
            name: name,
            category: "Main",
            area: "Test",
            countryOfOrigin: "GB",
            thumbnailURL: nil,
            instructions: "Cook it.",
            matchedSeasonalProduce: [],
            matchedSeasonalProduceCount: 0
        )
    }

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

    @Test func registrationRequiresValidFields() {
        #expect(
            AuthenticationFormRules.canSubmit(
                email: "cook@example.com",
                password: "password123",
                confirmation: "password123",
                isRegistering: true
            )
        )
        #expect(
            !AuthenticationFormRules.canSubmit(
                email: "cook@example.com",
                password: "password123",
                confirmation: "different",
                isRegistering: true
            )
        )
    }

    @Test func onboardingLegalPayloadIncludesCurrentTermsAcceptance() throws {
        let payload = PrivacyAcknowledgeRequest(
            acknowledged: true,
            termsAccepted: true,
            termsVersion: SeasonlyLegal.termsVersion
        )
        let data = try JSONEncoder().encode(payload)
        let json = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])

        #expect(json["acknowledged"] as? Bool == true)
        #expect(json["terms_accepted"] as? Bool == true)
        #expect(json["terms_version"] as? String == "2026-08-27")
    }

    @Test func legalDocumentsAreEmbeddedAndVersioned() {
        #expect(LegalDocument.termsOfUse.sections.count >= 10)
        #expect(LegalDocument.privacyNotice.sections.count >= 8)
        #expect(LegalDocument.termsOfUse.version == SeasonlyLegal.termsVersion)
        #expect(LegalDocument.privacyNotice.version == SeasonlyLegal.privacyNoticeVersion)
    }

    @Test func recipeFinderSkipsAlreadyUsedHigherRankedRecipes() throws {
        let first = recipe("First ranked")
        let second = recipe("Second ranked")

        let freshSelection = try #require(
            RecommendationSelectionRules.nextRecipe(
                from: [first, second],
                excluding: []
            )
        )
        let selected = try #require(
            RecommendationSelectionRules.nextRecipe(
                from: [first, second],
                excluding: [first.id]
            )
        )
        let fallback = try #require(
            RecommendationSelectionRules.nextRecipe(
                from: [first, second],
                excluding: [first.id, second.id]
            )
        )

        #expect(freshSelection.id == second.id)
        #expect(selected.id == second.id)
        #expect(fallback.id == first.id)
    }

    @Test func weeklyPlannerPreservesDinnerAndUsesUniqueRankedRecipes() {
        let existingRecipe = recipe("Already planned")
        let tuesdayRecipe = recipe("Tuesday dinner")
        let wednesdayRecipe = recipe("Wednesday dinner")
        let existingMeal = PlannedMeal(
            recipe: existingRecipe,
            day: .monday,
            meal: .dinner
        )

        let assignments = RecommendationSelectionRules.weeklyDinnerAssignments(
            from: [existingRecipe, tuesdayRecipe, tuesdayRecipe, wednesdayRecipe],
            preserving: [existingMeal]
        )

        #expect(assignments.map(\.day) == [.tuesday, .wednesday])
        #expect(assignments.map(\.recipe.id) == [tuesdayRecipe.id, wednesdayRecipe.id])
        #expect(Set(assignments.map(\.recipe.id)).count == assignments.count)
    }

}
