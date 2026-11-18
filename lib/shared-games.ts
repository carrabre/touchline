import "server-only";
import { scan, unpack } from "@/lib/aws";
import { matchStatsGame } from "@/lib/game-stats";
import { isLibraryMatch } from "@/lib/match-access";
import { parseReviewedRecord, reviewedStatsGame } from "@/lib/reviewed-goals";

export async function listReviewedGames() {
  const { Items } = await scan({
    FilterExpression: "#stage = :reviewed",
    ExpressionAttributeNames: { "#stage": "stage" },
    ExpressionAttributeValues: { ":reviewed": { S: "reviewed" } },
    ConsistentRead: true,
  });
  return Items.map((item) => reviewedStatsGame(parseReviewedRecord(JSON.parse(item.doc.S))));
}

export async function listStatsGames() {
  const { Items } = await scan({
    FilterExpression: "#stage <> :discarded",
    ExpressionAttributeNames: { "#stage": "stage" },
    ExpressionAttributeValues: { ":discarded": { S: "discarded" } },
    ConsistentRead: true,
  });
  return Items.flatMap((item) => {
    if (item.stage.S === "reviewed") return [reviewedStatsGame(parseReviewedRecord(JSON.parse(item.doc.S)))];
    const match = unpack(item);
    return isLibraryMatch(match) ? [matchStatsGame(match)] : [];
  }).sort((a, b) => Date.parse(b.date) - Date.parse(a.date));
}
