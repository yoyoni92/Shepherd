import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'
import { randomUUID } from 'crypto'

const bucket = process.env.S3_BUCKET_ACCIDENTS ?? 'shepherd-accidents'
const s3 = new S3Client({ region: process.env.AWS_REGION ?? 'us-east-1' })

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const form = await req.formData()
  const file = form.get('file') as File | null
  if (!file) return NextResponse.json({ error: 'no file' }, { status: 400 })

  const key = `accidents/${randomUUID()}/${file.name}`
  const bytes = await file.arrayBuffer()

  await s3.send(new PutObjectCommand({
    Bucket: bucket,
    Key: key,
    Body: Buffer.from(bytes),
    ContentType: file.type || 'application/octet-stream',
  }))

  return NextResponse.json({ file_url: `s3://${bucket}/${key}` })
}
